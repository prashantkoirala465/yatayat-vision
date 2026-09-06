from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Violation(Base):
    __tablename__ = "violations"
    # a track's violation should be recorded once - see the state machine's
    # own FLAGGED-is-terminal guarantee; this is the DB-level backstop.
    __table_args__ = (UniqueConstraint("source_id", "track_id", name="uq_violations_source_track"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str]  # which video/camera/session this came from
    track_id: Mapped[int]
    detected_at: Mapped[datetime]  # wall-clock time the violation was recorded
    speed_kmh: Mapped[float]
    evidence_frame_path: Mapped[str]
    plate_crop_path: Mapped[str | None] = mapped_column(default=None)
    plate_text: Mapped[str | None] = mapped_column(default=None)  # null until plate OCR (Module 5) is wired in
    status: Mapped[str] = mapped_column(default="pending_review")
