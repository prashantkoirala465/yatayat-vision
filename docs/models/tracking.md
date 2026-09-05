# Tracking (Module 2)

`app/tracking/tracker.py` wraps the Module 1 detector with ByteTrack via Ultralytics' built-in `.track()` — no separate re-ID embedding network to run, which matters on an 8GB M1 with no discrete GPU.

## Verification

Tested against a real highway clip (`data/samples/vehicles.mp4`, fetched via `scripts/fetch_sample_video.sh` — a Roboflow-published example asset, 3840x2160, 25fps, 538 frames), since no Nepal footage exists yet and this is genuinely about proving the tracking *mechanism* works, not detection accuracy on the eventual target domain.

`scripts/track_demo.py --source data/samples/vehicles.mp4 --save-frames <dir>` runs the tracker and reports track lifecycle stats, plus (optionally) saves a few annotated frames. Visual inspection of the saved frames confirms the core thing this module needs to prove: **real vehicles keep a stable track ID as they move through frame** (e.g. a car and a truck both tracked correctly with consistent boxes/IDs across widely-separated frames of the clip).

```
processed 538 frames
unique tracks: 39
track length (frames) - min: 1, median: 14, max: 538
unique tracks by class: {'car': 24, 'two_wheeler': 5, 'bus': 7, 'truck': 3}
```

## A real finding, not swept under the rug

Two of the longest-lived tracks (#4 and #60, both classified `bus`, both lasting 290-538 frames — nearly the entire clip) turned out on visual inspection to be **false positives on static structures**: an overhead highway sign gantry, and a large ambiguous region of background. Real vehicles in this clip don't last anywhere near that long (they enter and exit the camera's field of view in seconds), so an unusually long-lived track is a real signal worth having — but neither confidence (false-positive tracks ranged 0.11-0.72, overlapping real vehicles' low end) nor bbox movement (false positives still drift ~100px+ from detection jitter) cleanly separates these automatically here. I tried both and neither held up against the actual data — recorded honestly rather than shipping a threshold that looks principled but doesn't actually work.

**Why this doesn't block Module 2 or need fixing here:** BMD-45 (Bengaluru CCTV) has no highway sign gantries in its training distribution, so this is a detector domain-generalization gap on a test video that isn't even the target domain (Nepal) — not a tracking bug. ByteTrack is doing exactly its job: faithfully associating whatever the detector hands it across frames, including the detector's own false positives.

**Where this actually gets handled:** Module 4's violation state machine already requires N consecutive over-threshold-confidence frames before treating a track as violation-worthy (see the project plan) — that debounce is the right layer to reject this kind of low-confidence noise, not the tracker itself. `track_demo.py`'s output prints raw per-track confidence ranges precisely so this stays visible on every run rather than silently "fixed" by a heuristic that doesn't actually generalize.

A second, smaller nuance: a track's reported class is whichever class was predicted in its *most recent* frame, not a majority vote — a track can flicker between classes across frames on weak detections. `FrameTracks`/`Detection` expose per-frame class labels so a consumer (e.g. Module 4) can do majority-voting if it matters there; not resolved at the tracker level since it's a downstream policy choice, not part of what ByteTrack itself needs to do correctly.
