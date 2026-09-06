import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.queue import redis_conn, video_queue
from app.schemas import JobCreateResponse, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])

UPLOADS_DIR = Path("/tmp/yatayat_uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=JobCreateResponse)
async def create_job(file: UploadFile, speed_limit_kmh: float = 100.0):
    # Reads the whole upload into memory before writing it - fine for the
    # portfolio-scale videos this project deals with; a real production
    # deployment handling large files would stream this to disk in chunks.
    source_id = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    dest = UPLOADS_DIR / source_id
    dest.write_bytes(await file.read())

    # Enqueued by string path, not a direct import - process_video_job pulls
    # in the full ML stack (ultralytics, opencv, paddleocr), which only the
    # RQ worker process needs, not the API server itself.
    job = video_queue.enqueue("app.tasks.process_video_job", str(dest), source_id, speed_limit_kmh)
    return JobCreateResponse(job_id=job.id, source_id=source_id)


@router.get("/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        raise HTTPException(404, "job not found")
    return JobStatus(
        job_id=job.id,
        status=job.get_status(),
        result=job.result if job.is_finished else None,
        error=str(job.exc_info) if job.is_failed else None,
    )
