from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Violation

client = TestClient(app)


@pytest.fixture
def violation():
    session = SessionLocal()
    v = Violation(
        source_id="test-source",
        track_id=1,
        detected_at=datetime.now(timezone.utc),
        speed_kmh=88.5,
        evidence_frame_path="/tmp/does-not-need-to-exist.jpg",
    )
    session.add(v)
    session.commit()
    session.refresh(v)
    violation_id = v.id
    session.close()

    yield violation_id

    session = SessionLocal()
    session.query(Violation).filter(Violation.id == violation_id).delete()
    session.commit()
    session.close()


def test_get_violation(violation):
    response = client.get(f"/violations/{violation}")
    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "test-source"
    assert body["speed_kmh"] == 88.5
    assert body["status"] == "pending_review"
    assert body["plate_text"] is None


def test_get_violation_not_found():
    response = client.get("/violations/999999999")
    assert response.status_code == 404


def test_list_violations_includes_created(violation):
    response = client.get("/violations")
    assert response.status_code == 200
    ids = [v["id"] for v in response.json()]
    assert violation in ids


def test_list_violations_filters_by_status(violation):
    response = client.get("/violations", params={"status": "does-not-exist"})
    assert response.status_code == 200
    assert response.json() == []


def test_update_violation_plate_text(violation):
    response = client.patch(f"/violations/{violation}", json={"plate_text": "१२३४"})
    assert response.status_code == 200
    assert response.json()["plate_text"] == "१२३४"

    # persisted, not just echoed back
    response = client.get(f"/violations/{violation}")
    assert response.json()["plate_text"] == "१२३४"


def test_update_violation_can_explicitly_clear_plate_text(violation):
    """A reviewer clearing a bad correction back to null must actually work -
    caught as a real bug during manual testing: a naive `is not None` check
    can't distinguish "field omitted" from "field explicitly set to null"."""
    client.patch(f"/violations/{violation}", json={"plate_text": "१२३४"})

    response = client.patch(f"/violations/{violation}", json={"plate_text": None})
    assert response.status_code == 200
    assert response.json()["plate_text"] is None

    response = client.get(f"/violations/{violation}")
    assert response.json()["plate_text"] is None


def test_update_violation_omitted_field_is_untouched(violation):
    client.patch(f"/violations/{violation}", json={"plate_text": "१२३४"})

    response = client.patch(f"/violations/{violation}", json={"status": "confirmed"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["plate_text"] == "१२३४"  # untouched, since it wasn't in this request


def test_update_violation_status(violation):
    response = client.patch(f"/violations/{violation}", json={"status": "confirmed"})
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_update_violation_not_found():
    response = client.patch("/violations/999999999", json={"status": "confirmed"})
    assert response.status_code == 404


def test_evidence_not_found_for_missing_violation():
    response = client.get("/violations/999999999/evidence")
    assert response.status_code == 404


def test_plate_crop_missing_when_not_set(violation):
    response = client.get(f"/violations/{violation}/plate-crop")
    assert response.status_code == 404
