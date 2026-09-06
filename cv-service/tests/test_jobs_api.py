import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_job_enqueues_and_returns_job_id():
    response = client.post(
        "/jobs",
        files={"file": ("test.mp4", io.BytesIO(b"not a real video, just bytes for enqueue plumbing"), "video/mp4")},
        data={"speed_limit_kmh": 100.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"]
    assert body["source_id"].endswith("test.mp4")


def test_job_status_for_unknown_job_is_404():
    response = client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_job_status_reflects_queued_job():
    create_response = client.post(
        "/jobs",
        files={"file": ("test2.mp4", io.BytesIO(b"more placeholder bytes"), "video/mp4")},
        data={"speed_limit_kmh": 100.0},
    )
    job_id = create_response.json()["job_id"]

    status_response = client.get(f"/jobs/{job_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["job_id"] == job_id
    # no worker is running during this test, so it should still be queued/pending -
    # this test only proves the enqueue+status-lookup wiring, not that a worker
    # can actually process this (deliberately fake, non-video) file
    assert body["status"] in ("queued", "started", "failed")
