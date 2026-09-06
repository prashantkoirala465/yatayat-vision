"""End-to-end demo: detect -> track -> speed -> violation dedup -> plate
localization + OCR -> DB.

Verification tool, not part of the served API yet (that's Module 6). Proves
the full wiring works: a real video in, flagged violations with evidence
frames and (when readable) a plate crop + number landing in Postgres out.

Plate localization/OCR only runs on the single flagged frame per track, not
every frame of every vehicle - the expensive step is throttled by design
(see the project plan's Module 3 feasibility notes), matching how a
production system would actually budget this work.

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
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from app.calibration.homography import Calibration, bbox_bottom_center, speed_kmh_from_positions
from app.db import SessionLocal
from app.models import Violation
from app.plates.localization import PlateLocalizer
from app.plates.ocr_legacy import read_legacy_plate
from app.tracking.tracker import VehicleTracker
from app.tracking.violation_state_machine import ViolationStateMachine

# Illustrative only - see module docstring.
IMAGE_POINTS = [(192, 2150), (1839, 2150), (1344, 758), (1834, 730)]
WORLD_POINTS = [(0.0, 0.0), (7.0, 0.0), (0.0, 100.0), (7.0, 100.0)]

SPEED_WINDOW_FRAMES = 10  # rolling window for the per-track speed estimate fed to the state machine

# Debounce alone (N consecutive over-threshold frames) isn't enough to reject
# a persistent-but-low-confidence false positive, e.g. the static highway
# sign gantry from Module 2 (docs/models/tracking.md) - it was detected
# consistently frame after frame, just at ~0.3 confidence, and its bbox
# jitter alone was enough to read as a sustained "high speed." Requiring a
# minimum confidence rejects it while a real, cleanly-tracked vehicle stays
# well above this - see docs/models/violations.md for what this caught.
MIN_CONFIDENCE = 0.4


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
    args = parser.parse_args()

    source_id = args.source_id or Path(args.source).name
    evidence_dir = Path(args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    calibration = Calibration.from_point_correspondences(IMAGE_POINTS, WORLD_POINTS)
    state_machine = ViolationStateMachine(speed_limit_kmh=args.speed_limit, debounce_frames=args.debounce_frames)
    tracker = VehicleTracker(args.model)
    plate_localizer = PlateLocalizer(args.plate_model)

    track_positions: dict[int, deque] = {}
    flagged_count = 0

    session = SessionLocal()
    try:
        for frame_index, (frame, tracks) in enumerate(tracker.track_with_frames(args.source)):
            for det in tracks.detections:
                if det.confidence < MIN_CONFIDENCE:
                    continue
                positions = track_positions.setdefault(det.track_id, deque(maxlen=SPEED_WINDOW_FRAMES))
                positions.append((frame_index, bbox_bottom_center(det.xyxy)))
                if len(positions) < 2:
                    continue

                speed = speed_kmh_from_positions(list(positions), calibration, args.fps)
                flagged = state_machine.update(det.track_id, frame_index, speed)
                if flagged is None:
                    continue

                evidence_path = evidence_dir / f"{source_id}_track{flagged.track_id}_frame{flagged.frame_index}.jpg"
                cv2.imwrite(str(evidence_path), frame)

                plate_crop_path, plate_text = None, None
                x1, y1, x2, y2 = (int(v) for v in det.xyxy)
                vehicle_crop = frame[max(0, y1) : y2, max(0, x1) : x2]
                if vehicle_crop.size > 0:
                    plate_crop = plate_localizer.locate(vehicle_crop)
                    if plate_crop is not None and plate_crop.size > 0:
                        plate_crop_path = evidence_dir / f"{source_id}_track{flagged.track_id}_plate.jpg"
                        cv2.imwrite(str(plate_crop_path), plate_crop)
                        plate_crop_path = str(plate_crop_path)
                        plate_text = read_legacy_plate(plate_crop).number_text

                session.add(
                    Violation(
                        source_id=source_id,
                        track_id=flagged.track_id,
                        detected_at=datetime.now(timezone.utc),
                        speed_kmh=flagged.speed_kmh,
                        evidence_frame_path=str(evidence_path),
                        plate_crop_path=plate_crop_path,
                        plate_text=plate_text,
                    )
                )
                session.commit()
                flagged_count += 1
                print(
                    f"flagged: track {flagged.track_id} at {flagged.speed_kmh:.1f} km/h "
                    f"(frame {flagged.frame_index}, plate={plate_text!r})"
                )
    finally:
        session.close()

    print(f"\ndone. {flagged_count} violation(s) flagged and written to the database")


if __name__ == "__main__":
    main()
