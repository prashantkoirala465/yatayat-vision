# yatayat-vision

A computer-vision pipeline for Nepal traffic: detects and tracks vehicles in video, estimates real-world speed from a calibrated camera view, localizes and reads license plates, and flags speed violations into a review dashboard.

## Why

Nepal mandated new embossed, Devanagari-script vehicle plates for new registrations starting September 2025, while millions of older painted plates stay on the road for years. Embossed plates have no ink contrast, so the OCR approaches that work for typical license plates don't apply — reading them needs edge/relief-based character segmentation instead. Between that, Nepal's dense and heterogeneous traffic (motorcycles, auto-rickshaws, buses, cars all sharing the same lanes), and there being no automated speed/plate enforcement infrastructure to speak of, this is a real, current, and locally-specific problem rather than a reskin of a generic ANPR tutorial.

## Stack

- **Pipeline** (`cv-service/`): FastAPI, YOLO (Ultralytics) for detection, ByteTrack for tracking, OpenCV homography for speed estimation, PaddleOCR + a custom embossed-plate pipeline for reading plates
- **Dashboard** (`dashboard/`): Next.js, TypeScript, Tailwind
- **Storage**: Postgres for violation records, Redis + RQ for background video processing jobs
- **Training**: full training runs happen on Google Colab's free T4 tier — the M1 Air this was built on has no discrete GPU, and a full run there would take hours and thermal-throttle a fanless laptop. Local MPS (Apple Silicon) runs are still used for fast iteration/debugging on a small data subset before committing to the long Colab run

## Ethics

Read `docs/ethics-and-privacy.md` before anything else in this repo — it's short, and it's the part that matters most about a project like this.

## Local setup

Requires Docker, Python 3.12+, and Node 20+.

```bash
# 1. start postgres + redis
cd infra && docker compose up -d

# 2. backend
cd cv-service
cp ../.env.example .env
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# 3. frontend (new terminal)
cd dashboard
cp ../.env.example .env.local
npm install
npm run dev

# 4. background worker (new terminal) - processes uploaded videos: detect, track, speed, plate OCR
cd cv-service
.venv/bin/pip install -r requirements-train.txt  # the worker needs the full ML stack the API server doesn't
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES .venv/bin/rq worker video_processing --url redis://localhost:6379/0
```

A video uploaded through the dashboard sits queued until the worker is running. `OBJC_DISABLE_INITIALIZE_FORK_SAFETY` is only needed on macOS - RQ's default worker forks a subprocess per job, and macOS's Objective-C runtime crashes on fork() unless that guard is disabled. Not needed on Linux (including wherever this ends up deployed).

See `docs/architecture.md` for how the pieces fit together.

## Fully containerized demo

The above runs each piece on the host for fast iteration (hot reload). To run the whole system as containers instead - useful for a clean, reproducible demo rather than day-to-day development:

```bash
cd infra
docker compose --profile full up --build
```

This builds and starts postgres, redis, the API server, the worker (needs `cv-service/data/models/*.pt` to already exist locally - see `cv-service/data/README.md`), and the dashboard, all wired together. Dashboard at `http://localhost:3000`, API at `http://localhost:8000`. See `docs/deployment.md` for why this is a demo-time setup rather than an always-on hosted service.

## Working on model training/dataset scripts

`cv-service/scripts/` and `cv-service/notebooks/` need heavier ML dependencies the API service itself doesn't:

```bash
cd cv-service
.venv/bin/pip install -r requirements-train.txt
.venv/bin/python scripts/bmd45_subset_and_convert.py --scale 0.05 --out /tmp/bmd45_debug  # small local subset
```

That gives a fast local loop for debugging the pipeline (data conversion, training loop, checkpointing, export) on Apple Silicon's MPS backend before running the full-scale job on Colab — see `cv-service/notebooks/train_vehicle_detector.ipynb`.
