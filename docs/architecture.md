# Architecture

## Services

- **`cv-service/`** (FastAPI, Python) — owns Postgres and the entire CV pipeline: vehicle detection, tracking, speed estimation, plate localization, OCR, and violation deduplication. Long-running video/stream processing runs as background jobs via Redis + RQ.
  - The API server process and the RQ worker process are the same codebase but genuinely different runtime footprints: the API server (`app/main.py`) only needs FastAPI/SQLAlchemy/Redis-the-client to list violations and enqueue jobs, while the worker needs the full ML stack (Ultralytics, OpenCV, PaddleOCR, PyTorch) to actually run the pipeline. Jobs are enqueued by string import path (`"app.tasks.process_video_job"`), not a direct function reference, specifically so the API server never imports that heavy stack at all — see `docs/models/dashboard.md`.
- **`dashboard/`** (Next.js, TypeScript) — a pure API client. It has no direct database access; every violation record it shows comes from `cv-service`'s API.

## Pipeline (built up module by module — see the project plan for the full roadmap)

```
video/stream source
      |
      v
vehicle detection (YOLO)
      |
      v
tracking (ByteTrack, per-vehicle track_id)
      |
      v
speed estimation (homography-calibrated, per track)
      |
      v
plate localization + OCR (legacy painted -> PaddleOCR; embossed Devanagari -> custom pipeline)
      |
      v
violation dedup (per-track state machine) --> Postgres --> dashboard
```

## Why this split

Same reasoning as this project's sibling (Cortex): a real service boundary between the CV/ML backend and the review UI, rather than one monolithic app, mirrors how a production system like this would actually be composed — the pipeline is the part that has real compute/model requirements, the dashboard is a thin consumer of its output.
