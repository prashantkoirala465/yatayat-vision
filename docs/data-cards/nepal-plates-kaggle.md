# Vehicle Number Plate Dataset (Nepal) — Kaggle

Used for: the plate localization detector (Module 5).

## What it is

8,078 images with YOLO-format single-class ("plate") bounding box labels, already paired 1:1 (every image has a matching label file; some images have multiple plate boxes — up to 5, likely multi-vehicle frames). Images are vehicle-scale crops (roughly 50–450px), not full traffic-camera scenes — this dataset is meant to run **after** vehicle detection/cropping, matching this project's own cascaded design (Module 1's vehicle detector finds and crops a vehicle, this plate detector then finds the plate within that crop).

- Source: [`ishworsubedii/vehicle-number-plate-datasetnepal`](https://www.kaggle.com/datasets/ishworsubedii/vehicle-number-plate-datasetnepal) on Kaggle, downloaded via `kagglehub` (no account/API key needed for this dataset)
- License: Apache 2.0
- Collected in Kathmandu, Bhaktapur, and Lalitpur — the exact target geography for this project
- Full size: ~830MB — used wholesale (small enough that no subsetting is needed, unlike BMD-45)

## What was actually found inspecting it (not assumed)

- **Plates are painted, not embossed** — matches Module 5's "legacy plate" scope; the newer embossed Devanagari plates (Module 8) aren't represented here since this dataset predates that mandate.
- **A random sample is often illegible even to a human eye.** Visually inspected 8 randomly-sampled ground-truth crops: 6 of 8 were unreadable due to motion blur or low resolution, 2 were clearly legible. This is a real data-quality ceiling on OCR accuracy, not an OCR model limitation — worth remembering when interpreting any recognition accuracy number later, and arguably a realistic reflection of real-world traffic-camera image quality rather than a flaw specific to this dataset.
- **Not all plates are Devanagari script.** At least some plates in this dataset use English/Latin lettering (older-style Nepal plates, from before the Devanagari mandate) — a Devanagari-only OCR model reads these as garbled nonsense regardless of image quality, since it's simply the wrong model for that plate era. Not solved in Module 5 (see `docs/models/plate_ocr.md`) — treated as a documented open problem rather than blocking the plate detector, which doesn't care about script.
- **Nepal plates are two-line** (a province/class line above a registration-number line) — a single-line text recognizer performs far better when the crop is split top/bottom before recognition than when fed the whole two-line crop at once. See `docs/models/plate_ocr.md`.

## Split

No pre-existing train/val split — `scripts/nepal_plates_prep.py` creates one (85/15, fixed seed for reproducibility) as plain image-path list files (`train.txt`/`val.txt`), not copied directories — the images stay wherever `kagglehub` cached them, avoiding an unnecessary multi-hundred-MB copy.
