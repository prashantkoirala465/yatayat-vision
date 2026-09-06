"""Evaluate legacy plate OCR against ground-truth plate crops.

Uses the Kaggle dataset's own bounding boxes (not this project's own plate
detector, which doesn't need to exist yet for this) - isolates OCR quality
from detector quality. Reports the validator pass rate and confidence
distribution, which is what's actually measurable without ground-truth
TEXT labels (this dataset only has bounding boxes, not the plate text
itself - see docs/data-cards/nepal-plates-kaggle.md) - not per-character
accuracy against a true reading, which would need a labeled sample.

Usage:
    python scripts/plate_ocr_eval.py --sample-size 50
"""

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import kagglehub

from app.plates.ocr_legacy import read_legacy_plate

DATASET_REF = "ishworsubedii/vehicle-number-plate-datasetnepal"


def crop_first_plate(dataset_dir: Path, name: str):
    img = cv2.imread(str(dataset_dir / "images" / f"{name}.jpg"))
    h, w = img.shape[:2]
    with open(dataset_dir / "labels" / f"{name}.txt") as f:
        cx, cy, bw, bh = (float(v) for v in f.readline().split()[1:])
    x1, y1 = max(0, int((cx - bw / 2) * w)), max(0, int((cy - bh / 2) * h))
    x2, y2 = min(w, int((cx + bw / 2) * w)), min(h, int((cy + bh / 2) * h))
    return img[y1:y2, x1:x2]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    dataset_dir = Path(kagglehub.dataset_download(DATASET_REF)) / "vehicle_number_plate_detection"
    all_names = sorted(p.stem for p in (dataset_dir / "images").glob("*.jpg"))
    rng = random.Random(args.seed)
    sample = rng.sample(all_names, args.sample_size)

    passed, failed = [], []
    for name in sample:
        crop = crop_first_plate(dataset_dir, name)
        if crop.size == 0:
            continue
        reading = read_legacy_plate(crop)
        (passed if reading.number_text else failed).append((name, reading))

    print(f"sample size: {len(sample)}")
    print(f"validator pass rate: {len(passed)}/{len(sample)} ({100 * len(passed) / len(sample):.0f}%)")
    if passed:
        avg_conf = sum(r.number_confidence for _, r in passed) / len(passed)
        print(f"avg confidence (passed): {avg_conf:.2f}")
        print("passed examples:")
        for name, r in passed[:10]:
            print(f"  {name}: {r.number_text!r} (conf {r.number_confidence:.2f})")
    if failed:
        avg_conf = sum(r.number_confidence for _, r in failed) / len(failed)
        print(f"avg confidence (failed): {avg_conf:.2f}")


if __name__ == "__main__":
    main()
