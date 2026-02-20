"""Tests for tenant list and detail endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import os

os.environ.setdefault("FROSTBYTE_AUTH_BYPASS", "true")

from pipeline.main import app

client = TestClient(app)

FAKE_TENANT = {
    "tenant_id": "acme-corp",
    "state": "ACTIVE",
    "config": {"tier": "enterprise"},
    "config_version": 3,
    "created_at": "2026-01-01T00:00:00+00:00",
}


def _make_row(data: dict):
    """Create a mock asyncpg Record-like object."""
    m = MagicMock()
    m.__getitem__ = lambda self, k: data[k]
    m.keys = lambda: data.keys()
    return m


def test_list_tenants_requires_pool(monkeypatch):
    """Returns 503 when DB pool not initialized."""
    monkeypatch.setattr("pipeline.db._pool", None)
    resp = client.get("/api/v1/tenants")
    assert resp.status_code == 503


@patch("pipeline.routes.tenants._get_pool")
def test_list_tenants_200(mock_pool):
    pool = AsyncMock()
    pool.fetch.return_value = [_make_row(FAKE_TENANT)]
    pool.fetchval.return_value = 1
    mock_pool.return_value = pool

    resp = client.get("/api/v1/tenants")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] == 1
    assert body["items"][0]["id"] == "acme-corp"
    assert body["items"][0]["name"] == "acme-corp"


@patch("pipeline.routes.tenants._get_pool")
def test_list_tenants_pagination(mock_pool):
    pool = AsyncMock()
    pool.fetch.return_value = []
    pool.fetchval.return_value = 0
    mock_pool.return_value = pool

    resp = client.get("/api/v1/tenants?page=2&limit=5")
    assert resp.status_code == 200
    # Verify OFFSET calculated correctly: (page-1)*limit = 5
    call_args = pool.fetch.call_args[0]
    assert call_args[1] == 5   # LIMIT
    assert call_args[2] == 5   # OFFSET


@patch("pipeline.routes.tenants._get_pool")
def test_get_tenant_200(mock_pool):
    pool = AsyncMock()
    pool.fetchrow.return_value = _make_row(FAKE_TENANT)
    mock_pool.return_value = pool

    resp = client.get("/api/v1/tenants/acme-corp")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "acme-corp"
    assert body["state"] == "ACTIVE"


@patch("pipeline.routes.tenants._get_pool")
def test_get_tenant_404(mock_pool):
    pool = AsyncMock()
    pool.fetchrow.return_value = None
    mock_pool.return_value = pool

    resp = client.get("/api/v1/tenants/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "TENANT_NOT_FOUND"
