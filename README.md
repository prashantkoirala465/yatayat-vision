# yatayat-vision

A computer-vision pipeline for Nepal traffic: detects and tracks vehicles in video, estimates real-world speed from a calibrated camera view, localizes and reads license plates, and flags speed violations into a review dashboard.

## Why

Nepal mandated new embossed, Devanagari-script vehicle plates for new registrations starting September 2025, while millions of older painted plates stay on the road for years. Embossed plates have no ink contrast, so the OCR approaches that work for typical license plates don't apply — reading them needs edge/relief-based character segmentation instead. Between that, Nepal's dense and heterogeneous traffic (motorcycles, auto-rickshaws, buses, cars all sharing the same lanes), and there being no automated speed/plate enforcement infrastructure to speak of, this is a real, current, and locally-specific problem rather than a reskin of a generic ANPR tutorial.

## Stack

- **Pipeline** (`cv-service/`): FastAPI, YOLO (Ultralytics) for detection, ByteTrack for tracking, OpenCV homography for speed estimation, PaddleOCR + a custom embossed-plate pipeline for reading plates
- **Dashboard** (`dashboard/`): Next.js, TypeScript, Tailwind
- **Storage**: Postgres for violation records, Redis + RQ for background video processing jobs
- **Training**: Google Colab (free tier) — the M1 Air this was built on has no GPU, so all model training happens there and the exported weights run locally for inference

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
.venv/bin/uvicorn app.main:app --reload

# 3. frontend (new terminal)
cd dashboard
cp ../.env.example .env.local
npm install
npm run dev
```

See `docs/architecture.md` for how the pieces fit together.
