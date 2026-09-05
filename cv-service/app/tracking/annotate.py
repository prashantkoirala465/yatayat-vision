"""Draw tracked detections onto a frame - visual QA during development now,
reused for violation evidence frames once Module 4 needs them."""

import numpy as np
import supervision as sv

from app.tracking.tracker import FrameTracks

_BOX_ANNOTATOR = sv.BoxAnnotator(color_lookup=sv.ColorLookup.TRACK)
_LABEL_ANNOTATOR = sv.LabelAnnotator(color_lookup=sv.ColorLookup.TRACK)


def draw_frame(frame: np.ndarray, tracks: FrameTracks) -> np.ndarray:
    if not tracks.detections:
        return frame

    detections = sv.Detections(
        xyxy=np.array([d.xyxy for d in tracks.detections], dtype=np.float32),
        confidence=np.array([d.confidence for d in tracks.detections], dtype=np.float32),
        tracker_id=np.array([d.track_id for d in tracks.detections], dtype=int),
    )
    labels = [f"#{d.track_id} {d.class_name} {d.confidence:.2f}" for d in tracks.detections]

    annotated = _BOX_ANNOTATOR.annotate(scene=frame.copy(), detections=detections)
    return _LABEL_ANNOTATOR.annotate(scene=annotated, detections=detections, labels=labels)
