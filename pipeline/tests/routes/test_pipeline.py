"""Tests for pipeline status and config endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os

os.environ.setdefault("FROSTBYTE_AUTH_BYPASS", "true")

from pipeline.main import app

client = TestClient(app)


def test_pipeline_status_returns_200():
    resp = client.get("/api/v1/pipeline/status")
    assert resp.status_code == 200


def test_pipeline_status_shape():
    resp = client.get("/api/v1/pipeline/status")
    body = resp.json()
    assert "mode" in body
    assert "batch_size" in body
    assert "model" in body
    assert "throughput" in body
    assert "nodes" in body
    assert isinstance(body["nodes"], list)
    assert len(body["nodes"]) == 3


def test_pipeline_status_throughput_is_float():
    resp = client.get("/api/v1/pipeline/status")
    body = resp.json()
    assert isinstance(body["throughput"], float)


def test_patch_config_mode():
    resp = client.patch("/api/v1/config", json={"mode": "offline"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "offline"


def test_patch_config_batch_size_valid():
    resp = client.patch("/api/v1/config", json={"batch_size": 75})
    assert resp.status_code == 200
    assert resp.json()["batch_size"] == 75


def test_patch_config_batch_size_zero_rejected():
    resp = client.patch("/api/v1/config", json={"batch_size": 0})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "VALIDATION_ERROR"


def test_patch_config_batch_size_too_large_rejected():
    resp = client.patch("/api/v1/config", json={"batch_size": 257})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "VALIDATION_ERROR"


def test_patch_config_persists_to_status():
    client.patch("/api/v1/config", json={"mode": "dual", "batch_size": 50})
    resp = client.get("/api/v1/pipeline/status")
    body = resp.json()
    assert body["mode"] == "dual"
    assert body["batch_size"] == 50
