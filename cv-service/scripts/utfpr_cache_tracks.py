"""Run the tracker once over the UTFPR validation video and cache raw
per-frame detections to JSON, so the (expensive, ~9min) tracking pass doesn't
need re-running while iterating on ground-truth matching/scoring logic.

Usage: python scripts/utfpr_cache_tracks.py --source /tmp/utfpr_check/video.mp4 --out /tmp/utfpr_check/tracks.json
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tracking.tracker import VehicleTracker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--model", default="data/models/best.pt")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    tracker = VehicleTracker(args.model)
    frames_out = []
    for frame_index, tracks in enumerate(tracker.track(args.source)):
        frames_out.append(
            {
                "frame": frame_index,
                "detections": [
                    {"track_id": d.track_id, "class_name": d.class_name, "confidence": d.confidence, "xyxy": d.xyxy}
                    for d in tracks.detections
                ],
            }
        )
        if frame_index % 1000 == 0:
            print(f"processed frame {frame_index}")

    Path(args.out).write_text(json.dumps(frames_out))
    print(f"wrote {len(frames_out)} frames to {args.out}")


if __name__ == "__main__":
    main()
