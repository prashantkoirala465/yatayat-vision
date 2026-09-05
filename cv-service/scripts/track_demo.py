"""Run the tracker against a video and report track lifecycle stats.

Verification tool for Module 2 - not part of the served API. Confirms track
IDs stay stable across frames (a real vehicle keeps one ID) rather than
fragmenting into a new ID every few frames, and optionally saves a handful of
annotated frames for a visual sanity check.

Usage:
    python scripts/track_demo.py --source data/samples/vehicles.mp4
    python scripts/track_demo.py --source data/samples/vehicles.mp4 --save-frames /tmp/track_qa --num-frames 5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `app.*` resolves when run directly

import cv2

from app.tracking.annotate import draw_frame
from app.tracking.tracker import VehicleTracker


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True)
    parser.add_argument("--model", default="data/models/best.pt")
    parser.add_argument("--save-frames", help="directory to save a few annotated frames into, for visual QA")
    parser.add_argument("--num-frames", type=int, default=5)
    args = parser.parse_args()

    tracker = VehicleTracker(args.model)

    save_dir = Path(args.save_frames) if args.save_frames else None
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(args.source)
    frame_count_hint = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    save_at_frames = set()
    if save_dir and frame_count_hint > 0:
        step = max(1, frame_count_hint // args.num_frames)
        save_at_frames = set(range(0, frame_count_hint, step))

    track_first_seen: dict[int, int] = {}
    track_last_seen: dict[int, int] = {}
    track_class: dict[int, str] = {}
    track_confidences: dict[int, list[float]] = {}
    total_frames = 0

    for frame_index, (frame, tracks) in enumerate(tracker.track_with_frames(args.source)):
        total_frames += 1
        for det in tracks.detections:
            track_first_seen.setdefault(det.track_id, frame_index)
            track_last_seen[det.track_id] = frame_index
            track_class[det.track_id] = det.class_name
            track_confidences.setdefault(det.track_id, []).append(det.confidence)

        if save_dir and frame_index in save_at_frames:
            annotated = draw_frame(frame, tracks)
            out_path = save_dir / f"frame_{frame_index:04d}.jpg"
            cv2.imwrite(str(out_path), annotated)
            print(f"saved {out_path}")

    track_lengths = {tid: track_last_seen[tid] - track_first_seen[tid] + 1 for tid in track_first_seen}

    print(f"\nprocessed {total_frames} frames")
    print(f"unique tracks: {len(track_first_seen)}")
    if track_lengths:
        lengths = sorted(track_lengths.values())
        print(f"track length (frames) - min: {lengths[0]}, median: {lengths[len(lengths) // 2]}, max: {lengths[-1]}")
    by_class: dict[str, int] = {}
    for cls in track_class.values():
        by_class[cls] = by_class.get(cls, 0) + 1
    print(f"unique tracks by class: {by_class}")

    # Raw diagnostic, not an automated classifier: a track lasting nearly the
    # whole clip is inherently suspicious for a highway scene where vehicles
    # keep moving through frame - but confidence/movement alone don't cleanly
    # separate these from real vehicles here, so print the numbers and let a
    # human look, rather than pretending a threshold catches it reliably.
    # See docs/models/vehicle_detector.md for what this surfaced.
    print("\nlongest-lived tracks (length, confidence range) - eyeball for suspiciously long/low-confidence ones:")
    for tid, length in sorted(track_lengths.items(), key=lambda kv: -kv[1])[:8]:
        confs = track_confidences[tid]
        print(f"  track {tid} ({track_class[tid]}): {length} frames, conf {min(confs):.2f}-{max(confs):.2f}")


if __name__ == "__main__":
    main()
