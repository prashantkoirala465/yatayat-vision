"""Validates the OCR'd registration-number line of a Nepal plate.

Deliberately narrow: only the number line (2-4 Devanagari digits), not the
full province/vehicle-class line above it. That top line's format varies
(province name abbreviation + zone digit + a vehicle-class letter) and OCR
reads it far less reliably than the number line (see docs/models/plate_ocr.md)
- validating a format we can't recognize with any confidence would be
false precision, not a real check.

Strict on purpose: rejects anything with extra characters (e.g. trailing
OCR noise) rather than trying to strip and salvage a near-match. Reporting
"unreadable" honestly beats silently accepting a partially-garbled read.
"""

import re

DEVANAGARI_DIGITS = "०१२३४५६७८९"
_NUMBER_PATTERN = re.compile(f"^[{DEVANAGARI_DIGITS}]{{2,4}}$")


def is_plausible_plate_number(text: str) -> bool:
    return bool(_NUMBER_PATTERN.match(text.strip()))
