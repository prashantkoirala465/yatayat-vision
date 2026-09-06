from datetime import datetime

from pydantic import BaseModel


class ViolationOut(BaseModel):
    id: int
    source_id: str
    track_id: int
    detected_at: datetime
    speed_kmh: float
    evidence_frame_path: str
    plate_crop_path: str | None
    plate_text: str | None
    status: str

    model_config = {"from_attributes": True}


class ViolationUpdate(BaseModel):
    """For the Module 6 human-review workflow: a reviewer can correct the
    OCR'd plate text or change the review status. Both optional - a PATCH
    only touches the fields it's given."""

    plate_text: str | None = None
    status: str | None = None


class JobCreateResponse(BaseModel):
    job_id: str
    source_id: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: int | None = None
    error: str | None = None
