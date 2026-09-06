# Speed estimation (Module 3)

`app/calibration/homography.py` maps tracked image points to real-world ground-plane coordinates via a homography, and computes speed from a point's displacement over time. Known simplification: assumes a flat road plane and a pinhole model with no lens-distortion correction — fine for an MVP, not a survey-grade measurement.

## Synthetic validation (proves the math)

`scripts/validate_speed_synthetic.py` builds a known homography (4 image points ↔ 4 real-world points describing a 3.5m-wide, 40m-long road segment), simulates a point moving at an exact known speed (72 km/h), and confirms `speed_kmh_from_positions()` recovers it:

```
known speed:     72.0000 km/h
recovered speed: 72.0000 km/h
error:           0.000000%
```

This proves the geometry and arithmetic have no bugs, independent of any detector/tracker noise or external dataset availability — the right first validation step regardless of what real-world data is or isn't available.

## Real-world validation: what was actually tried

The plan called for validating against BrnoCompSpeed's LIDAR ground truth. That turned out to not be freely accessible (their README requires emailing the dataset authors directly, and their calibration method is vanishing-point-based rather than homography, so even with access it wouldn't directly cross-check this code). Went looking for alternatives instead of settling for synthetic-only:

- **pNEUMA** — genuinely free (Zenodo), but ships only post-processed trajectories (lat/lon, speed), no raw video or pixel data — nothing for this pipeline to actually process.
- **highD** — real drone-trajectory ground truth, but gated behind an access-request form, and drone/overhead geometry doesn't match a roadside camera anyway.
- **UTFPR (Luvizón et al., IEEE T-ITS 2017)** — genuinely public (Google Drive, verified downloadable with `gdown`, no request needed), real radar-measured ground truth speeds with exact frame ranges, and even ships its own homography calibration matrices per lane. Looked very promising. Running the actual detector+tracker+calibration pipeline against it surfaced two real things:
  1. A real matching bug on my end, since fixed: their ground-truth "region" is a **license-plate** bounding box (their method tracks plates specifically, per the paper), not a whole-vehicle box — matching by IoU against a whole-vehicle detection will never work; a containment/center check against the plate position is the correct comparison.
  2. A real, more fundamental mismatch: their camera is a **near-overhead intersection view** (confirmed by inspecting actual frames from two different videos in the dataset), chosen specifically because it keeps rear plates visible without occlusion. That's a very different geometry from both BMD-45's training distribution (angled CCTV) and the angled roadside-camera style Nepal footage will use. Forcing a full pipeline test here would mostly measure "does the detector handle an overhead angle it's never seen" rather than "is the speed math correct" — a different, already-answered question.

Not treated as a dead end to paper over: it confirmed a real detector-domain question worth remembering (camera angle matters a lot for how well this detector generalizes) and the matching-logic bug fix is real, reusable work.

- **VS13** (audio-video vehicle speed dataset) — also genuinely public (direct HTTP download, verified by actually downloading a full sample: 400 videos across 13 vehicle models, each a single vehicle passing at a known, cruise-control-held speed). Confirmed by extracting and viewing real frames: this one **does** use a low, angled roadside camera (~0.5m from the road, ~1.2m high) — the right geometry, unlike UTFPR. Real license plates are clearly visible throughout, which matters because VS13 ships no calibration matrix at all — deriving one would mean building a plate-width-based reference calibration (520mm standardized EU/Montenegro plate width), the same core technique the UTFPR paper itself uses. That's legitimate future work, but it's genuinely new work (a plate localization step doesn't exist yet - it's a later module's job), not a quick check, so it was intentionally not pushed further right now.

## Where this leaves Module 3

The speed math is proven correct (synthetic validation). A full real-world pipeline validation (detector + tracker + calibration together, checked against independent ground truth) remains open — not because suitable data doesn't exist, but because doing it properly either needs a plate-localization step that isn't built yet (VS13) or a detector retrain for a camera angle outside its current training distribution (UTFPR). The honest path forward is to revisit this once real Nepal footage exists, which needs its own calibration built from scratch anyway (Module 7), or to come back to VS13 once plate localization exists (Module 5).
