"""Build a Nepal-relevant subset of BMD-45 and convert it to YOLO format.

Downloads only the annotation JSON plus the selected images from
iisc-aim/BMD-45 on Hugging Face (never the full ~153GB dataset), merges
BMD-45's 13 fine-grained vehicle categories into 6 classes relevant to
Nepal traffic, and writes a YOLO-format dataset (images/ + labels/ per
split, a data.yaml, and a manifest.json documenting exactly what was
selected and why). Rationale for the class mapping and sampling method
is in docs/data-cards/bmd45.md.

Usage:
    python scripts/bmd45_subset_and_convert.py                      # full subset
    python scripts/bmd45_subset_and_convert.py --scale 0.03 --out /tmp/bmd45_smoke  # quick local check
"""

import argparse
import json
import os
import random
import shutil
import time

# Xet (HF's newer chunked-transfer protocol) rate-limits unauthenticated
# requests hard, and Colab's shared IP pool trips it almost immediately -
# this must be set before huggingface_hub is imported, since it's read once
# into a module-level constant at import time. Falls back to plain HTTP,
# which is slower but far more tolerant of anonymous/shared-IP use.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from huggingface_hub import hf_hub_download
from PIL import Image

REPO_ID = "iisc-aim/BMD-45"

# BMD-45's 13 categories collapse to 6 classes: the downstream task (track a
# vehicle, estimate its speed, read its plate) doesn't need car-body-style
# granularity, and merging lets a small subset budget spend its images on
# classes that actually differ in detection difficulty (two-wheelers,
# three-wheelers) rather than splitting hairs between a Hatchback and a Sedan.
CATEGORY_MERGE = {
    "Two-wheeler": "two_wheeler",
    "Hatchback": "car",
    "Sedan": "car",
    "SUV": "car",
    "MUV": "car",
    "Van": "car",
    "Three-wheeler": "three_wheeler",
    "Bus": "bus",
    "Mini-bus": "bus",
    "Tempo-traveller": "bus",
    "Truck": "truck",
    "LCV": "truck",
    "Bicycle": "bicycle",
}
CLASS_NAMES = ["two_wheeler", "car", "three_wheeler", "bus", "truck", "bicycle"]
CLASS_IDS = {name: i for i, name in enumerate(CLASS_NAMES)}

# Rarest-first: quota filling below prioritizes underrepresented classes so a
# small budget doesn't end up 90% two-wheelers, which is what a purely random
# sample of BMD-45 would produce (two-wheelers appear in ~90% of images).
BUCKET_ORDER = ["bicycle", "bus", "truck", "three_wheeler", "car", "two_wheeler"]

SPLITS = {
    "train": {"repo_dir": "BMD-45-Train", "budget": 4000, "per_class_target": 900},
    "val": {"repo_dir": "BMD-45-Val", "budget": 800, "per_class_target": 200},
}


def _with_retry(fn, *args, retries: int = 6, base_delay: float = 5.0, **kwargs):
    """Retries transient failures (rate limits, flaky Colab networking) with
    exponential backoff. Hugging Face's 429s are usually gone within a minute."""
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if attempt == retries - 1:
                raise
            delay = base_delay * (2**attempt)
            print(f"  download failed ({exc}); retrying in {delay:.0f}s ({attempt + 1}/{retries})")
            time.sleep(delay)


def download_annotations(repo_dir: str, cache_dir: Path) -> dict:
    path = _with_retry(
        hf_hub_download,
        REPO_ID,
        f"{repo_dir}/_annotations.coco.json",
        repo_type="dataset",
        local_dir=str(cache_dir),
    )
    with open(path) as f:
        return json.load(f)


def select_images(coco: dict, budget: int, per_class_target: int, seed: int) -> set:
    """Greedy rarest-first quota fill. Returns a set of selected image_ids."""
    id2name = {c["id"]: c["name"] for c in coco["categories"]}
    bucket_images: dict[str, set] = {name: set() for name in CLASS_NAMES}
    for ann in coco["annotations"]:
        if ann.get("iscrowd"):
            continue
        bucket = CATEGORY_MERGE[id2name[ann["category_id"]]]
        bucket_images[bucket].add(ann["image_id"])

    rng = random.Random(seed)
    selected: set = set()
    for bucket in BUCKET_ORDER:
        if len(selected) >= budget:
            break
        already = len(bucket_images[bucket] & selected)
        need = max(0, per_class_target - already)
        if need == 0:
            continue
        pool = list(bucket_images[bucket] - selected)
        rng.shuffle(pool)
        for image_id in pool[:need]:
            if len(selected) >= budget:
                break
            selected.add(image_id)
    return selected


def coco_bbox_to_yolo(bbox, img_w: float, img_h: float):
    x_min, y_min, w, h = bbox
    x_center = (x_min + w / 2) / img_w
    y_center = (y_min + h / 2) / img_h
    clamp = lambda v: min(max(v, 0.0), 1.0)
    return clamp(x_center), clamp(y_center), clamp(w / img_w), clamp(h / img_h)


def build_split(split_name: str, cfg: dict, out_dir: Path, seed: int, workers: int) -> dict:
    cache_dir = out_dir / "_hf_cache"
    coco = download_annotations(cfg["repo_dir"], cache_dir)
    id2name = {c["id"]: c["name"] for c in coco["categories"]}
    selected_ids = select_images(coco, cfg["budget"], cfg["per_class_target"], seed)

    images_by_id = {im["id"]: im for im in coco["images"] if im["id"] in selected_ids}
    anns_by_image: dict[int, list] = {i: [] for i in images_by_id}
    for ann in coco["annotations"]:
        if ann.get("iscrowd") or ann["image_id"] not in images_by_id:
            continue
        anns_by_image[ann["image_id"]].append(ann)

    images_dir = out_dir / split_name / "images"
    labels_dir = out_dir / split_name / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    def flat_stem(file_name: str) -> str:
        rel = Path(file_name)
        # BMD-45 shards images across images_000/, images_001/, ... - namespace
        # the flattened filename by shard so we can't collide on a bare numeric id.
        return f"{rel.parent.name}__{rel.stem}"

    def fetch_one(image_id: int):
        info = images_by_id[image_id]
        # BMD-45's source PNGs run ~3.5MB each - at subset scale (thousands of
        # images) that's tens of GB, easily exhausting a free Google Drive
        # account. Re-encoding to JPEG here cuts that by roughly 5-10x; quality
        # 90 is well above what a detector needs and this is a training-input
        # copy, not an archival one.
        dest = images_dir / f"{flat_stem(info['file_name'])}.jpg"
        if dest.exists():
            return image_id, None
        try:
            src = _with_retry(
                hf_hub_download,
                REPO_ID,
                f"{cfg['repo_dir']}/{info['file_name']}",
                repo_type="dataset",
                local_dir=str(cache_dir),
                retries=4,
                base_delay=3.0,
            )
        except Exception as exc:  # a single flaky download shouldn't kill the whole run
            return image_id, str(exc)
        try:
            with Image.open(src) as im:
                im.convert("RGB").save(dest, "JPEG", quality=90)
        except Exception as exc:
            return image_id, f"failed to re-encode as jpeg: {exc}"
        finally:
            Path(src).unlink(missing_ok=True)  # reclaim space immediately, don't keep both copies
        return image_id, None

    failures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_one, iid): iid for iid in images_by_id}
        for fut in as_completed(futures):
            image_id, err = fut.result()
            if err:
                failures.append((image_id, err))
    failed_ids = {image_id for image_id, _ in failures}

    bucket_counts = {name: 0 for name in CLASS_NAMES}
    for image_id, info in images_by_id.items():
        if image_id in failed_ids:
            continue
        lines = []
        seen_buckets = set()
        for ann in anns_by_image[image_id]:
            bucket = CATEGORY_MERGE[id2name[ann["category_id"]]]
            x, y, w, h = coco_bbox_to_yolo(ann["bbox"], info["width"], info["height"])
            if w <= 0 or h <= 0:
                continue
            lines.append(f"{CLASS_IDS[bucket]} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
            seen_buckets.add(bucket)
        stem = flat_stem(info["file_name"])
        (labels_dir / f"{stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
        for b in seen_buckets:
            bucket_counts[b] += 1

    return {
        "split": split_name,
        "requested_budget": cfg["budget"],
        "images_selected": len(images_by_id) - len(failed_ids),
        "images_failed": len(failed_ids),
        "per_class_image_counts": bucket_counts,
    }


def write_data_yaml(out_dir: Path):
    names = "\n".join(f"  {i}: {name}" for i, name in enumerate(CLASS_NAMES))
    content = f"path: {out_dir}\ntrain: train/images\nval: val/images\nnames:\n{names}\n"
    (out_dir / "data.yaml").write_text(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="data/bmd45_subset")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="multiply every split's budget/target by this (use e.g. 0.03 for a quick local smoke test)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {"source": REPO_ID, "seed": args.seed, "scale": args.scale, "class_names": CLASS_NAMES, "splits": []}
    for split_name, cfg in SPLITS.items():
        scaled_cfg = {
            "repo_dir": cfg["repo_dir"],
            "budget": max(1, int(cfg["budget"] * args.scale)),
            "per_class_target": max(1, int(cfg["per_class_target"] * args.scale)),
        }
        print(f"building {split_name}: budget={scaled_cfg['budget']} per_class_target={scaled_cfg['per_class_target']}")
        result = build_split(split_name, scaled_cfg, out_dir, args.seed, args.workers)
        print(result)
        manifest["splits"].append(result)

    write_data_yaml(out_dir)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"done. dataset at {out_dir}")


if __name__ == "__main__":
    main()
