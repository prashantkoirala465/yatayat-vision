"""CLI wrapper around app.pipeline.process_video - see that module for the
actual pipeline logic (also used by the RQ background job, app/tasks.py).

The calibration below is ILLUSTRATIVE, not measured - four points picked off
a visible highway lane in data/samples/vehicles.mp4, assuming a standard
3.5m lane width and a guessed ~100m depth between the near and far reference
lines. Module 3's synthetic test already proves the homography/speed math
itself is correct; this script's job is proving the pipeline wiring around
it, not producing a trustworthy absolute speed for this specific clip - see
docs/models/speed_estimation.md for why real-world calibration validation is
deferred rather than faked here.

Usage:
    python scripts/violation_demo.py --source data/samples/vehicles.mp4 --speed-limit 100
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.calibration.homography import Calibration
from app.pipeline import PipelineConfig, process_video

IMAGE_POINTS = [(192, 2150), (1839, 2150), (1344, 758), (1834, 730)]
WORLD_POINTS = [(0.0, 0.0), (7.0, 0.0), (0.0, 100.0), (7.0, 100.0)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True)
    parser.add_argument("--model", default="data/models/best.pt")
    parser.add_argument("--plate-model", default="data/models/plate_detector.pt")
    parser.add_argument("--fps", type=float, default=25.0)
    parser.add_argument("--speed-limit", type=float, required=True)
    parser.add_argument("--debounce-frames", type=int, default=5)
    parser.add_argument("--evidence-dir", default="/tmp/violation_evidence")
    parser.add_argument("--source-id", default=None, help="defaults to the source filename")
    parser.add_argument(
        "--simulate-live",
        action="store_true",
        help="pace a recorded file to arrive like a live feed, instead of processing it as fast as possible",
    )
    args = parser.parse_args()

    source_id = args.source_id or Path(args.source).name
    calibration = Calibration.from_point_correspondences(IMAGE_POINTS, WORLD_POINTS)
    config = PipelineConfig(
        vehicle_model_path=args.model,
        plate_model_path=args.plate_model,
        calibration=calibration,
        fps=args.fps,
        speed_limit_kmh=args.speed_limit,
        debounce_frames=args.debounce_frames,
        evidence_dir=args.evidence_dir,
        simulate_live=args.simulate_live,
    )
    count = process_video(args.source, source_id, config)
    print(f"done. {count} violation(s) flagged and written to the database")


if __name__ == "__main__":
    main()
