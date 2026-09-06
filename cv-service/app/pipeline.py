"""The actual video-processing pipeline: detect -> track -> speed -> violation
dedup -> plate localization + OCR -> DB.

One implementation, two callers: the RQ background job (app/tasks.py) for
the served API, and scripts/violation_demo.py for CLI/manual runs - both
need the exact same logic, so it lives here rather than being duplicated.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2

from app.calibration.homography import Calibration, bbox_bottom_center, speed_kmh_from_positions
from app.db import SessionLocal
from app.models import Violation
from app.plates.localization import PlateLocalizer
from app.plates.ocr_legacy import read_legacy_plate
from app.tracking.tracker import VehicleTracker
from app.tracking.violation_state_machine import ViolationStateMachine

SPEED_WINDOW_FRAMES = 10  # rolling window for the per-track speed estimate fed to the state machine

# Debounce alone (N consecutive over-threshold frames) isn't enough to reject
# a persistent-but-low-confidence false positive, e.g. the static highway
# sign gantry from Module 2 (docs/models/tracking.md). Requiring a minimum
# detection confidence rejects it while a real, cleanly-tracked vehicle stays
# well above this - see docs/models/violations.md for what this caught.
DEFAULT_MIN_CONFIDENCE = 0.4


@dataclass
class PipelineConfig:
    vehicle_model_path: str
    plate_model_path: str
    calibration: Calibration
    fps: float
    speed_limit_kmh: float
    debounce_frames: int = 5
    evidence_dir: str = "/tmp/violation_evidence"
    min_confidence: float = DEFAULT_MIN_CONFIDENCE


def process_video(source: str, source_id: str, config: PipelineConfig) -> int:
    """Runs the full pipeline against `source`, writing flagged violations to
    the database. Returns the number of violations flagged."""
    evidence_dir = Path(config.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    state_machine = ViolationStateMachine(speed_limit_kmh=config.speed_limit_kmh, debounce_frames=config.debounce_frames)
    tracker = VehicleTracker(config.vehicle_model_path)
    plate_localizer = PlateLocalizer(config.plate_model_path)

    track_positions: dict[int, deque] = {}
    flagged_count = 0

    session = SessionLocal()
    try:
        for frame_index, (frame, tracks) in enumerate(tracker.track_with_frames(source)):
            for det in tracks.detections:
                if det.confidence < config.min_confidence:
                    continue
                positions = track_positions.setdefault(det.track_id, deque(maxlen=SPEED_WINDOW_FRAMES))
                positions.append((frame_index, bbox_bottom_center(det.xyxy)))
                if len(positions) < 2:
                    continue

                speed = speed_kmh_from_positions(list(positions), config.calibration, config.fps)
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
                        plate_path = evidence_dir / f"{source_id}_track{flagged.track_id}_plate.jpg"
                        cv2.imwrite(str(plate_path), plate_crop)
                        plate_crop_path = str(plate_path)
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
    finally:
        session.close()

    return flagged_count
