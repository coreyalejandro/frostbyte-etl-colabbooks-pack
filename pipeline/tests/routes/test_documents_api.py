"""Tests for document list and chain-of-custody endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import os
from datetime import datetime, timezone

os.environ.setdefault("FROSTBYTE_AUTH_BYPASS", "true")

from pipeline.main import app

client = TestClient(app)

NOW = datetime.now(timezone.utc)

FAKE_DOC = {
    "id": "11111111-1111-1111-1111-111111111111",
    "tenant_id": "acme-corp",
    "filename": "contract.pdf",
    "status": "completed",
    "modality": "text",
    "custom_metadata": {"source": "upload"},
    "created_at": NOW,
    "updated_at": NOW,
    "total": 1,
}

FAKE_EVENT = {
    "event_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "event_type": "DOCUMENT_INGESTED",
    "timestamp": NOW,
    "actor": "system",
    "details": {"size": 1024},
}


def _make_row(data: dict):
    m = MagicMock()
    m.__getitem__ = lambda self, k: data[k]
    return m


def test_list_documents_503_no_pool(monkeypatch):
    monkeypatch.setattr("pipeline.db._pool", None)
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 503


@patch("pipeline.routes.documents._get_pool")
def test_list_documents_200(mock_pool):
    pool = AsyncMock()
    pool.fetch.return_value = [_make_row(FAKE_DOC)]
    mock_pool.return_value = pool

    resp = client.get("/api/v1/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["items"][0]["metadata"] == {"source": "upload"}


@patch("pipeline.routes.documents._get_pool")
def test_list_documents_tenant_filter(mock_pool):
    pool = AsyncMock()
    pool.fetch.return_value = [_make_row(FAKE_DOC)]
    mock_pool.return_value = pool

    resp = client.get("/api/v1/documents?tenantId=acme-corp")
    assert resp.status_code == 200
    call_args = pool.fetch.call_args[0]
    assert "acme-corp" in call_args


@patch("pipeline.routes.documents._get_pool")
def test_get_document_chain_200(mock_pool):
    pool = AsyncMock()
    pool.fetchrow.return_value = _make_row({"id": FAKE_DOC["id"]})
    pool.fetch.return_value = [_make_row(FAKE_EVENT)]
    mock_pool.return_value = pool

    doc_id = FAKE_DOC["id"]
    resp = client.get(f"/api/v1/documents/{doc_id}/chain")
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == doc_id
    assert isinstance(body["events"], list)
    assert body["events"][0]["action"] == "DOCUMENT_INGESTED"
    assert body["events"][0]["performed_by"] == "system"


@patch("pipeline.routes.documents._get_pool")
def test_get_document_chain_404(mock_pool):
    pool = AsyncMock()
    pool.fetchrow.return_value = None
    mock_pool.return_value = pool

    resp = client.get("/api/v1/documents/nonexistent-uuid/chain")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "DOCUMENT_NOT_FOUND"
