# BMD-45

Used for: the vehicle detector's training data (Module 1).

## What it is

A large-scale vehicle detection dataset built from Bengaluru's Safe City CCTV network: 45,986 images (35,792 train / 10,194 val), 1920×1080, 13 fine-grained vehicle categories, annotated in COCO format. Published alongside a CVPR 2026 Findings paper specifically because existing detection benchmarks (COCO, UA-DETRAC) are tuned for orderly Western/Chinese traffic and generalize poorly to the dense, heterogeneous traffic common in South Asian cities — auto-rickshaws, tempos, and motorcycles sharing lanes with cars and buses, which is a much closer match to Nepal's actual traffic than any alternative we found.

- Source: [`iisc-aim/BMD-45`](https://huggingface.co/datasets/iisc-aim/BMD-45) on Hugging Face
- License: CC BY 4.0
- Full size: ~153GB — not used wholesale (see below)

## Why not the full dataset

A free Colab session has ephemeral disk and a time-boxed GPU allocation. 153GB doesn't fit that workflow, and full-scale training isn't needed for a portfolio-scale detector fine-tuned from COCO-pretrained weights. `cv-service/scripts/bmd45_subset_and_convert.py` downloads only the two annotation JSON files plus a selected subset of images — never the full image set.

## Category mapping

BMD-45's 13 categories collapse to 6 classes. The downstream task (track a vehicle, estimate its speed, read its plate) doesn't need car-body-style granularity — a Hatchback and a Sedan are the same problem for tracking and speed estimation. Merging lets a small subset budget spend its images on classes that actually differ in detection difficulty instead of splitting hairs:

| BMD-45 category | Merged class |
|---|---|
| Two-wheeler | `two_wheeler` |
| Hatchback, Sedan, SUV, MUV, Van | `car` |
| Three-wheeler | `three_wheeler` |
| Bus, Mini-bus, Tempo-traveller | `bus` |
| Truck, LCV | `truck` |
| Bicycle | `bicycle` |

## Subset method

Two-wheelers appear in ~90% of BMD-45's images; Bicycle, Mini-bus, and Tempo-traveller each appear in well under 5%. A uniform random sample at subset scale would end up dominated by two-wheelers and could easily miss the rare classes almost entirely. Instead, `select_images()` in the script:

1. Buckets every image by which merged classes it contains.
2. Processes classes rarest-first (`bicycle → bus → truck → three_wheeler → car → two_wheeler`).
3. For each class, samples enough not-yet-selected images to reach a per-class target image count (default 900/train, 200/val), skipping classes that are already satisfied by overlap with images picked for an earlier (rarer) class.
4. Stops once the overall image budget (4000 train / 800 val) is hit.

Because a single image can satisfy several classes at once (e.g. a frame with both a bicycle and a truck), the actual number of images selected is typically well below the raw budget cap once every class's target is met — this is expected, not a bug, and the true counts are recorded in `manifest.json` alongside the seed used (`42`, for reproducibility) after each run.

## Operational note: Hugging Face rate limiting on Colab

Colab's shared IP pool trips Hugging Face's Xet transfer protocol's rate limit almost immediately for unauthenticated requests (`429` on the very first download). Setting `HF_HUB_DISABLE_XET=1` alone turned out not to be reliable across environments/versions — Colab kept using Xet regardless. The notebook now uninstalls the `hf_xet` package outright in its setup cell, which forces `huggingface_hub` onto the plain HTTP downloader unconditionally (no env-var/version ambiguity possible if the package genuinely isn't importable). The subsetting script also retries transient failures with exponential backoff, and the notebook supports an optional `HF_TOKEN` Colab secret for a higher rate-limit ceiling. None of this was needed running the same script locally (a single, non-shared IP never hit it) — it's specifically a Colab-and-many-anonymous-users problem.

## Operational note: Google Drive storage

BMD-45's source PNGs run ~3.5MB each. An early version of the training notebook persisted the full downloaded image subset to Google Drive so it would survive across sessions — at full subset scale (~4800 images) that alone is enough to fill a free Drive account (hit `0 MB free disk space` mid-run in practice). Two fixes: images are now re-encoded to JPEG (quality 90, ~5-10x smaller) immediately after download, and the dataset subset lives on Colab's **local** disk rather than Drive at all — only training checkpoints, exported weights, and a small manifest get persisted to Drive. The subset is cheap and deterministic to rebuild each session (same seed, same result), so there's no real cost to not persisting it.

## Known limitations

- Bengaluru CCTV camera angles/heights and road markings aren't identical to whatever camera setup ends up used for Nepal footage — this is a transfer-learning assumption (detector generalizes across camera geometry reasonably well at the vehicle-detection task), not a guarantee. Worth re-checking once real Nepal footage is available in a later module.
- The merge mapping is a deliberate simplification for this project's needs; a project that cared about vehicle-type classification (e.g. for tolling) would want the original 13-class granularity instead.
