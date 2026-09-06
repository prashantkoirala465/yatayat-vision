from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Violation
from app.schemas import ViolationOut, ViolationUpdate

router = APIRouter(prefix="/violations", tags=["violations"])


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.get("", response_model=list[ViolationOut])
def list_violations(status: str | None = None, session: Session = Depends(get_session)):
    query = session.query(Violation).order_by(Violation.detected_at.desc())
    if status:
        query = query.filter(Violation.status == status)
    return query.all()


@router.get("/{violation_id}", response_model=ViolationOut)
def get_violation(violation_id: int, session: Session = Depends(get_session)):
    violation = session.get(Violation, violation_id)
    if violation is None:
        raise HTTPException(404, "violation not found")
    return violation


@router.patch("/{violation_id}", response_model=ViolationOut)
def update_violation(violation_id: int, update: ViolationUpdate, session: Session = Depends(get_session)):
    violation = session.get(Violation, violation_id)
    if violation is None:
        raise HTTPException(404, "violation not found")
    # exclude_unset, not a None check - a reviewer clearing plate_text back
    # to null via {"plate_text": null} needs to be distinguishable from the
    # field being omitted from the request entirely, and a plain `is not
    # None` check on the model can't tell those apart.
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(violation, field, value)
    session.commit()
    session.refresh(violation)
    return violation


@router.get("/{violation_id}/evidence")
def get_evidence_frame(violation_id: int, session: Session = Depends(get_session)):
    violation = session.get(Violation, violation_id)
    if violation is None:
        raise HTTPException(404, "violation not found")
    return FileResponse(violation.evidence_frame_path)


@router.get("/{violation_id}/plate-crop")
def get_plate_crop(violation_id: int, session: Session = Depends(get_session)):
    violation = session.get(Violation, violation_id)
    if violation is None or violation.plate_crop_path is None:
        raise HTTPException(404, "no plate crop for this violation")
    return FileResponse(violation.plate_crop_path)
