"""Plate localization within a vehicle crop, using the Module 5 detector.

Runs on a single vehicle-scale crop, not a full frame - matches how the
Kaggle training data was structured (docs/data-cards/nepal-plates-kaggle.md)
and the cascaded design (vehicle detector finds+crops a vehicle, this then
finds the plate within it), not a from-scratch full-frame search.
"""

from pathlib import Path

import numpy as np
from ultralytics import YOLO


class PlateLocalizer:
    def __init__(self, model_path: str | Path):
        self._model = YOLO(str(model_path))

    def locate(self, vehicle_crop: np.ndarray, conf: float = 0.3) -> np.ndarray | None:
        """Returns the highest-confidence plate crop within vehicle_crop, or
        None if nothing clears the confidence threshold."""
        results = self._model.predict(vehicle_crop, conf=conf, verbose=False)
        boxes = results[0].boxes
        if len(boxes) == 0:
            return None
        best_idx = int(boxes.conf.argmax())
        x1, y1, x2, y2 = (int(v) for v in boxes.xyxy[best_idx].tolist())
        return vehicle_crop[y1:y2, x1:x2]
