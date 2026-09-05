# cv-service/data/

Gitignored — local dataset subsets and trained/exported model weights live here but are never committed (too large, and derived/regenerable from code + a fixed seed).

- `models/` — exported weights copied down from a Colab training run (`best.pt`, `best.onnx`, `best.mlpackage`, `training_manifest.json`). See `docs/models/vehicle_detector.md` for what the current copy actually achieved and how to regenerate it.
- `samples/` — real test video(s) for local tracking/speed-estimation development. Regenerate with `scripts/fetch_sample_video.sh`.
