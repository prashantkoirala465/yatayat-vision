# Violation detection & dedup (Module 4)

`app/tracking/violation_state_machine.py` is a per-track state machine: `NORMAL → VIOLATING` (after N consecutive over-threshold frames, debounced) `→ FLAGGED` (emitted once, then permanently silent for that track). track_id already gives "same vehicle across frames" for free (Module 2), so this is the only new logic needed to turn a stream of per-frame speeds into a deduplicated violation event.

Pure logic, no video/DB dependency — covered by real unit tests (`tests/test_violation_state_machine.py`, 5 cases: debounce window, sub-threshold streaks never flagging, a below-limit frame resetting the streak, flag-at-most-once, and independent per-track state).

## Schema

`violations` table (`app/models.py`, migrated via Alembic): `source_id` + `track_id` (unique together — a DB-level backstop on top of the state machine's own single-flag guarantee), `detected_at`, `speed_kmh`, `evidence_frame_path`, `plate_crop_path`/`plate_text` (nullable until Module 5 wires in plate OCR), `status` (defaults to `pending_review`, for the Module 6 human-review workflow).

## End-to-end verification, and a real bug it caught

`scripts/violation_demo.py` wires the full chain — detector → tracker → speed (using an *illustrative* calibration on `data/samples/vehicles.mp4`, not a validated one, see `docs/models/speed_estimation.md` for why rigorous calibration is deferred) → state machine → Postgres + saved evidence frame — and it immediately surfaced a real gap:

The Module 2 finding (a low-confidence, long-lived false-positive track on a static highway sign gantry) **passed the debounce check**. Its bbox jitter alone was consistent enough, frame after frame, to read as a sustained ~150 km/h "vehicle" even though debounce was working exactly as designed (5 consecutive over-threshold frames, genuinely sustained). Confirmed by re-drawing that exact frame with the track's box overlaid — same coordinates as the Module 2 gantry finding.

Debounce dedupes *repeated* signal; it was never going to filter *low-quality* signal, and this made that gap concrete instead of hypothetical. The fix: require a minimum detection confidence (0.4) before a detection even reaches the state machine. The gantry artifact sits at ~0.30 confidence; a real, cleanly-tracked vehicle in this clip sits at 0.46–0.87. Re-running with the filter: the gantry stopped flagging, the one genuine (if roughly-calibrated) vehicle still did.

```
flagged: track 24 at 111.9 km/h (frame 28)
done. 1 violation(s) flagged and written to the database
```

Verified in Postgres directly (`source_id`, `track_id`, `speed_kmh`, `status='pending_review'`, `evidence_frame_path`) and the saved evidence JPEG.

## Known limitations (by design, not oversight)

- The illustrative calibration means the *speed number* for this specific clip isn't trustworthy — the point of this demo was the pipeline wiring and the confidence-filter fix, both of which are real.
- A confidence floor is a real improvement but not a complete one — a false positive that happened to sit above 0.4 for 5+ consecutive frames would still slip through. No further heuristic is layered on top right now; the honest position (also true of the Module 2 movement/confidence attempts) is that this needs more signal than track-level speed+confidence alone, which is exactly what plate verification (Module 5) will add for anything that actually reaches a human reviewer.
- ID-switch-driven double-counting (Module 3's plan) remains an accepted MVP limitation, unchanged this module.
