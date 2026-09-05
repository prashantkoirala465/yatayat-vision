# Architecture

## Services

- **`cv-service/`** (FastAPI, Python) — owns Postgres and the entire CV pipeline: vehicle detection, tracking, speed estimation, plate localization, OCR, and violation deduplication. Long-running video/stream processing runs as background jobs via Redis + RQ.
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
