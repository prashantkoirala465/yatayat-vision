"""Per-vehicle tracking on top of the Module 1 detector.

ByteTrack via Ultralytics' built-in `.track()` - no separate re-ID embedding
network to run, which matters on an 8GB M1 with no discrete GPU. See
docs/architecture.md for where this sits in the overall pipeline.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    track_id: int
    class_name: str
    confidence: float
    xyxy: tuple[float, float, float, float]


@dataclass
class FrameTracks:
    frame_index: int
    detections: list[Detection]


class VehicleTracker:
    """Wraps a trained YOLO detector with ByteTrack, exposing a plain
    per-frame stream of tracked detections instead of raw Ultralytics
    Results objects - keeps everything downstream (annotation, violation
    dedup) decoupled from the Ultralytics API surface."""

    def __init__(self, model_path: str | Path, tracker_config: str = "bytetrack.yaml"):
        self._model = YOLO(str(model_path))
        self._tracker_config = tracker_config

    def track(self, source: str | Path) -> Iterator[FrameTracks]:
        """Lightweight stream for consumers that only need track metadata
        (e.g. violation dedup) - doesn't hold onto frame pixel data."""
        for _, tracks in self.track_with_frames(source):
            yield tracks

    def track_with_frames(self, source: str | Path) -> Iterator[tuple[np.ndarray, FrameTracks]]:
        """Same stream, paired with the raw frame - for anything that needs
        to draw on or crop from it (annotation, evidence capture)."""
        results = self._model.track(
            source=str(source),
            tracker=self._tracker_config,
            persist=True,
            stream=True,
            verbose=False,
        )
        for frame_index, result in enumerate(results):
            tracks = FrameTracks(frame_index=frame_index, detections=_to_detections(result))
            yield result.orig_img, tracks


def _to_detections(result) -> list[Detection]:
    boxes = result.boxes
    if boxes.id is None:
        # a frame can have zero tracked detections (e.g. nothing above the
        # confidence threshold, or the tracker hasn't confirmed a track yet)
        return []
    return [
        Detection(
            track_id=int(track_id),
            class_name=result.names[int(cls)],
            confidence=float(conf),
            xyxy=tuple(float(v) for v in xyxy),
        )
        for track_id, cls, conf, xyxy in zip(
            boxes.id.tolist(), boxes.cls.tolist(), boxes.conf.tolist(), boxes.xyxy.tolist()
        )
    ]
