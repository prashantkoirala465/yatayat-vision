"""OCR for legacy (painted, ink-contrast) Nepal plates.

Nepal plates are two lines (province/zone/vehicle-class above, registration
number below) - PaddleOCR's Devanagari recognizer performs far better on
each line split apart than on the whole two-line crop at once (0.71-0.81
confidence on real crops vs ~0.20 feeding the whole crop, see
docs/models/plate_ocr.md for the actual numbers this is based on).

Known open problem, not solved here: this only handles Devanagari-script
plates. Some legacy Nepal plates use English/Latin lettering (pre-mandate),
which this model reads as noise - see docs/models/plate_ocr.md.
"""

from dataclasses import dataclass

import numpy as np
from paddleocr import TextRecognition

from app.plates.format_validator import is_plausible_plate_number

_MODEL_NAME = "devanagari_PP-OCRv5_mobile_rec"
_model: TextRecognition | None = None


def _get_model() -> TextRecognition:
    global _model
    if _model is None:
        _model = TextRecognition(model_name=_MODEL_NAME)
    return _model


@dataclass
class PlateReading:
    number_text: str | None  # None if unreadable or fails format validation
    number_confidence: float
    top_line_text: str  # best-effort context, not format-validated - see module docstring
    top_line_confidence: float


def read_legacy_plate(plate_crop: np.ndarray, top_fraction: float = 0.52, overlap_fraction: float = 0.08) -> PlateReading:
    height = plate_crop.shape[0]
    split_row = int(height * top_fraction)
    top = plate_crop[:split_row]
    bottom = plate_crop[max(0, split_row - int(height * overlap_fraction)) :]

    model = _get_model()
    top_result = model.predict(top)[0]
    bottom_result = model.predict(bottom)[0]

    number_text = bottom_result["rec_text"].strip()
    valid = is_plausible_plate_number(number_text)

    return PlateReading(
        number_text=number_text if valid else None,
        number_confidence=bottom_result["rec_score"],
        top_line_text=top_result["rec_text"].strip(),
        top_line_confidence=top_result["rec_score"],
    )
