"""Tests for verification test endpoint."""
import os

os.environ.setdefault("FROSTBYTE_AUTH_BYPASS", "true")

from fastapi.testclient import TestClient
from pipeline.main import app

client = TestClient(app)


def test_verification_red_team_200():
    resp = client.post("/api/v1/verification/test", json={"testType": "red-team"})
    assert resp.status_code == 200
    body = resp.json()
    assert "score" in body
    assert "details" in body
    assert isinstance(body["score"], int)
    assert isinstance(body["details"], list)


def test_verification_compliance_200():
    resp = client.post("/api/v1/verification/test", json={"testType": "compliance"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] != client.post(
        "/api/v1/verification/test", json={"testType": "red-team"}
    ).json()["score"]


def test_verification_penetration_200():
    resp = client.post("/api/v1/verification/test", json={"testType": "penetration"})
    assert resp.status_code == 200


def test_verification_details_shape():
    resp = client.post("/api/v1/verification/test", json={"testType": "red-team"})
    details = resp.json()["details"]
    assert len(details) > 0
    for item in details:
        assert "test" in item
        assert "passed" in item
        assert "message" in item


def test_verification_missing_test_type_422():
    resp = client.post("/api/v1/verification/test", json={})
    assert resp.status_code == 422


def test_verification_unknown_test_type_400():
    resp = client.post("/api/v1/verification/test", json={"testType": "unknown"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "INVALID_TEST_TYPE"
