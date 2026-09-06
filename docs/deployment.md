# Deployment & hosting (Module 9)

## What's containerized

Both services are Dockerized, reflecting the real API/worker split from `docs/architecture.md`:

- `infra/Dockerfile.cv-service-api` — the FastAPI server. Small, fast-building image (lean `requirements.txt` only).
- `infra/Dockerfile.cv-service-worker` — the RQ worker that actually runs the CV pipeline. Much bigger image (torch, ultralytics, paddleocr) and takes real minutes to build, since it installs the same heavy stack `requirements-train.txt` does. Bakes in the trained model weights at build time — they're gitignored (too large, regenerable, see `cv-service/data/README.md`), so this image can only be built on a machine that already has `cv-service/data/models/*.pt` from a completed training run.
- `infra/Dockerfile.dashboard` — Next.js, using its `output: "standalone"` build so the image only carries the runtime deps a request actually needs, not the full `node_modules` tree.

`infra/docker-compose.yml` wires all five services (postgres, redis, cv-api, cv-worker, dashboard) together behind a `full` profile — `docker compose --profile full up --build` brings up the entire system in containers with one command. Plain `docker compose up` (no profile) still gives just postgres+redis, for the host-based dev workflow in the root `README.md` (hot-reload `uvicorn --reload` / `npm run dev`, not a container rebuild per code change).

**A known, deliberate tradeoff in the worker image**: it builds `linux/amd64` (see the comment in `docker-compose.yml` on why - paddlepaddle has no linux aarch64 wheel), and on Linux, PyPI's plain `torch==2.14.0` wheel pulls in `nvidia-cudnn-cu13` and other CUDA packages as pip dependencies even though this container has no GPU and never touches them - torch just runs on CPU regardless of whether they're present. The obvious fix (installing from `download.pytorch.org/whl/cpu` instead) doesn't apply here: that index's newest published build for `cp312`/`linux_x86_64` is `2.6.0+cpu`, and this project already pins `torch==2.14.0` for the local macOS dev/training-debug environment (`requirements-train.txt`) - downgrading just for this one image would trade a real, working version match for a smaller download, and introduce exactly the kind of version drift this project has been careful to avoid elsewhere (see the Python 3.14→3.12 rebuild story in `docs/models/*`). Verified this doesn't affect correctness, just image size (adds a few GB of unused CUDA/cuDNN libraries) - an accepted cost given how infrequently this image gets rebuilt in this project's demo-hours-only usage pattern.

## Why this isn't hosted publicly and always-on

The expensive part of this system is the worker: it's running a real detector + tracker + OCR pipeline per uploaded video, on CPU (no GPU in this project's budget, consistent with training happening on free Colab rather than a paid GPU instance throughout). Keeping that warm continuously on a paid host, for a portfolio project nobody is querying most of the time, doesn't make sense — either it sits idle burning money, or it's on a free tier tiny enough that a real video upload times out or gets OOM-killed.

The honest, sustainable answer for a project like this is **demo-hours-only**: run `docker compose --profile full up --build` locally (or on a free-tier host, spun up for the duration of a call) when actually giving a demo, not as a service sitting on the public internet waiting for traffic. This is the same free/local-first approach used throughout this project (Colab for training, local M1 for inference) rather than reaching for a paid always-on option that doesn't get meaningfully more value out of a small, bursty demo workload.

If this ever needed to genuinely run continuously (e.g. real traffic cameras, not demo uploads), the actual production shape would separate concerns further: an autoscaled worker pool sized to camera count, a real object store instead of local disk for evidence frames, and per-camera calibration lookups instead of the one hardcoded calibration `app/tasks.py` currently uses. None of that is built now — there's no real camera and no second customer calling for it yet, and building it speculatively would just be unused code to maintain.

## Two real bugs the containerized run caught (not found by inspection)

Actually uploading a real video through the running `--profile full` stack surfaced two things that reading the Dockerfiles/compose file wouldn't have:

1. **Uploads and evidence frames weren't shared between containers.** `cv-api` writes an uploaded video to `/tmp/yatayat_uploads` and the pipeline later writes evidence frames/plate crops to `/tmp/violation_evidence` - fine when both processes share one filesystem (the host-based dev workflow), but `cv-api` and `cv-worker` are separate containers once each has its own image. The first real upload failed with `FileNotFoundError: /tmp/yatayat_uploads/... does not exist` in the worker, and violations with evidence images would have silently 404'd from the API even if that hadn't happened. Fixed with two named volumes (`uploads`, `evidence`) mounted at those same paths in both `cv-api` and `cv-worker`.
2. **RQ's 180s default job timeout is too short for real CPU inference**, and considerably too short under the `linux/amd64` emulation the worker needs on Apple Silicon (see above) - the first real job died with `JobTimeoutException` mid-inference. Fixed by passing `job_timeout=1800` on enqueue (`app/routers/jobs.py`). Native x86_64 hardware would likely need much less, but there's no reason to cut it close for a demo-hours-only workload.

After both fixes, a real upload through the containerized stack went upload → queued → running → finished (3 violations flagged) → evidence frame and plate crop both downloadable through the API → both rendering correctly in the dashboard - verified end-to-end, not just "the containers started."

## Repo visibility

The repo stays private for now — that's the user's call to make when the portfolio piece is ready to show, not something to flip automatically as part of finishing a module.
