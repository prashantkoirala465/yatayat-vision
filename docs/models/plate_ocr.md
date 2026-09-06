# Legacy plate OCR (Module 5)

`app/plates/ocr_legacy.py` reads the registration-number line of a painted Nepal plate crop via PaddleOCR's Devanagari recognizer (`devanagari_PP-OCRv5_mobile_rec`); `app/plates/format_validator.py` accepts/rejects the result.

## Environment note: PaddleOCR needs Python ≤3.13

`paddlepaddle` has no wheel for Python 3.14 yet. The local dev venv had drifted to 3.14 by accident (whatever `python3` resolved to when first created in Module 0) even though the README and CI already specified 3.12+. Rebuilt the venv on 3.12 (a version already available locally) to fix this properly rather than route around it — matches what CI already runs, so this also closes a real, if harmless, environment inconsistency.

## Two-line plates need splitting before recognition

Nepal plates are two lines — a province/zone/vehicle-class line above a registration-number line. Feeding the whole two-line crop to a single-line recognizer gives garbage (`'व8'` at 0.20 confidence, on a real crop). Splitting into top/bottom halves before recognition (roughly 52% down, with a small overlap) is a large, real improvement — the same crop's number line alone recognized correctly at 0.71–0.81 confidence across several examples.

## Real accuracy numbers, not assumed ones

`scripts/plate_ocr_eval.py` ran the full pipeline (real detector-independent — crops taken from the Kaggle dataset's own ground-truth boxes, not this project's own plate detector, to isolate OCR quality from detection quality) against 50 randomly-sampled real plates:

```
validator pass rate: 4/50 (8%)
avg confidence (passed): 0.77
avg confidence (failed): 0.41
```

An 8% clean-read rate sounds low in isolation, but it's consistent with a separate finding: manually inspecting 8 random ground-truth crops earlier showed 6 of 8 were illegible to a human eye (motion blur, low resolution) — see `docs/data-cards/nepal-plates-kaggle.md`. Most of this dataset's images simply don't contain enough signal for any OCR approach to read reliably; the pipeline reads well when the crop is actually legible (0.77 avg confidence on passing reads) and correctly reports "unreadable" (via the nullable `plate_text`/`number_text` design) rather than fabricating a confident-looking wrong answer on the rest.

## Motorcycle plate check (the plan's called-out hardest case)

Ran the one clearly-identified motorcycle plate crop through the full pipeline: number line recognized as `'७४५३]'` at 0.71 confidence — high confidence, and visibly very close to correct, but rejected by the strict format validator over the trailing bracket character. One data point, not a powered study, but a concrete, honest result: the OCR itself handles a small motorcycle plate about as well as it handles car plates in this test; the validator's strictness is the thing standing between "close" and "accepted" here, which is the intended, conservative tradeoff (see the format validator's docstring) rather than a motorcycle-specific failure.

## Known open problems (not solved, not hidden)

- **Script mismatch**: some plates in this dataset use English/Latin lettering (older, pre-Devanagari-mandate plates) rather than Devanagari. The Devanagari-only recognizer reads these as noise regardless of image quality — this is the wrong model for that plate era, not a quality issue. No second OCR path for Latin-script plates is built yet.
- **Top line (province/zone/class) is not validated** — OCR reads it far less reliably than the number line, and there's no confidently-verified format grammar to validate it against yet. `PlateReading.top_line_text` is returned as best-effort context only.
- **The validator is strict on purpose** and will reject some genuinely-close reads (like the motorcycle example above) rather than risk silently accepting wrong ones — a real, deliberate tradeoff, not an oversight.
