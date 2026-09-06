"""Build a train/val split for the Nepal plate detection dataset.

Downloads via kagglehub (no API key needed for this public dataset) and
writes plain image-path list files rather than copying anything - the
dataset is already in YOLO format with images/ and labels/ as sibling
directories with matching filenames, which is exactly the layout Ultralytics
expects to auto-locate labels from an image path, so there's nothing to
convert. See docs/data-cards/nepal-plates-kaggle.md for what's actually in
this dataset (including real caveats: many crops are illegible, some plates
are English-script not Devanagari).

Usage:
    python scripts/nepal_plates_prep.py --out data/nepal_plates
"""

import argparse
import random
from pathlib import Path

import kagglehub

DATASET_REF = "ishworsubedii/vehicle-number-plate-datasetnepal"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="data/nepal_plates")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-fraction", type=float, default=0.15)
    args = parser.parse_args()

    dataset_path = Path(kagglehub.dataset_download(DATASET_REF))
    images_dir = dataset_path / "vehicle_number_plate_detection" / "images"
    labels_dir = dataset_path / "vehicle_number_plate_detection" / "labels"

    image_paths = sorted(p for p in images_dir.glob("*.jpg") if (labels_dir / f"{p.stem}.txt").exists())
    print(f"found {len(image_paths)} images with matching labels")

    rng = random.Random(args.seed)
    rng.shuffle(image_paths)
    split_idx = int(len(image_paths) * (1 - args.val_fraction))
    train_paths, val_paths = image_paths[:split_idx], image_paths[split_idx:]

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "train.txt").write_text("\n".join(str(p) for p in train_paths) + "\n")
    (out_dir / "val.txt").write_text("\n".join(str(p) for p in val_paths) + "\n")
    (out_dir / "data.yaml").write_text(f"path: {out_dir}\ntrain: train.txt\nval: val.txt\nnames:\n  0: plate\n")

    print(f"train: {len(train_paths)} images, val: {len(val_paths)} images")
    print(f"wrote {out_dir}/data.yaml")


if __name__ == "__main__":
    main()
