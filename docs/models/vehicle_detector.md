# Vehicle detector (Module 1)

## Result

Fine-tuned YOLO11n, 50 epochs on Colab's free T4, from COCO-pretrained weights. Final epoch on the held-out val split:

| Metric | Value |
|---|---|
| Precision | 0.796 |
| Recall | 0.741 |
| mAP50 | 0.810 |
| mAP50-95 | 0.638 |

Solid for a nano model fine-tuned on a modest subset — good enough to build tracking on top of (Module 2). Not claimed as state-of-the-art; a larger subset or a bigger base model (YOLO11s/m) would likely push mAP50-95 higher if that becomes worth the extra Colab time later.

## What it was actually trained on

Per `bmd45_subset_and_convert.py`'s quota-fill logic (see `docs/data-cards/bmd45.md`), the realized subset came in below the raw budget cap once every class's per-class target was satisfied through overlap:

| Split | Images | two_wheeler | car | three_wheeler | bus | truck | bicycle |
|---|---|---|---|---|---|---|---|
| train | 1862 | 1729 | 1386 | 1278 | 971 | 900 | 954 |
| val | 422 | 396 | 321 | 282 | 218 | 200 | 213 |

## Local verification

Ran the exported ONNX model against 4 fresh images (not the ones shown above, downloaded separately) via `ultralytics`' ONNX Runtime backend on the M1 (CPU). All four produced multi-class detections with high confidence (0.91–0.96 top confidence per image), correctly picking up two_wheeler/car/three_wheeler/bus/bicycle across different frames — confirms the exported model works end-to-end for local inference, not just inside the training notebook.

## Files

Not committed (gitignored under `cv-service/data/`, per `cv-service/.gitignore`) — regenerate by re-running `cv-service/notebooks/train_vehicle_detector.ipynb` on Colab (same seed, same result) and copying the exports down:

- `cv-service/data/models/best.pt` — PyTorch checkpoint
- `cv-service/data/models/best.onnx` — used for the local M1 smoke test above
- `cv-service/data/models/best.mlpackage` — CoreML, for native Apple Silicon acceleration (not yet benchmarked against the ONNX path)
- `cv-service/data/models/training_manifest.json` — copy of the dataset manifest this specific run trained on
