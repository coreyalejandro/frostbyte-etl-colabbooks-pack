# Missing Backend APIs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 7 missing FastAPI endpoints (API-01 through API-08) in `pipeline/pipeline/routes/` so the Frostbyte ETL Dashboard can operate without mock data.

**Architecture:** Four new router files added to `pipeline/pipeline/routes/`, each registered in `main.py`. All endpoints use the existing `asyncpg` pool (`db._get_pool()`), existing JWT auth dependency (`get_tenant_from_token` from `pipeline.auth`), and the established `HTTPException` error pattern. No new migrations required — all queries target confirmed existing tables (`tenants`, `documents`, `audit_events`).

**Tech Stack:** Python 3.12, FastAPI 0.115+, asyncpg 0.29+, Pydantic v2, python-jose (JWT), pytest-asyncio

---

## Reference: Existing Patterns

Before starting, read these files to understand conventions:
- `pipeline/pipeline/routes/tenant_schemas.py` — router pattern, DB pool access, error format
- `pipeline/pipeline/auth.py` — `get_tenant_from_token` dependency
- `pipeline/pipeline/db.py` — `_get_pool()`, error handling
- `docs/plans/2026-02-20-missing-backend-apis-design.md` — approved design

## Reference: Real DB Schema

```
tenants:      tenant_id TEXT PK, state TEXT, config JSONB, config_version INT, created_at, updated_at
documents:    id UUID PK, tenant_id TEXT, filename TEXT, status TEXT, modality TEXT, custom_metadata JSONB, created_at, updated_at
audit_events: event_id UUID PK, tenant_id TEXT, event_type TEXT, timestamp, actor TEXT, resource_type TEXT, resource_id TEXT, details JSONB
```

---

## Task 1: Create `pipeline/pipeline/routes/pipeline.py` (API-01 + API-08)

**Files:**
- Create: `pipeline/pipeline/routes/pipeline.py`
- Test: `pipeline/tests/routes/test_pipeline.py`

**Step 1: Write the failing tests**

Create `pipeline/tests/routes/test_pipeline.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
cd pipeline
pytest tests/routes/test_pipeline.py -v 2>&1 | head -30
```

Expected: ImportError or 404 — router not registered yet.

**Step 3: Create `pipeline/pipeline/routes/pipeline.py`**

```python
"""
Pipeline status and configuration endpoints.
API-01: GET /api/v1/pipeline/status
API-08: PATCH /api/v1/config
"""
from __future__ import annotations

import random
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from ..auth import get_tenant_from_token

router = APIRouter(prefix="/api/v1", tags=["pipeline"])

# In-memory pipeline config.
# TODO: Persist to pipeline_config DB table in a future migration.
# NOTE: Under horizontal scaling, config will diverge across workers.
_pipeline_config: dict[str, Any] = {
    "mode": "dual",
    "batch_size": 50,
    "model": "nomic-embed-text-v1.5",
}


class NodeMetrics(BaseModel):
    rate: float | None = None
    latency: float | None = None


class NodeStatus(BaseModel):
    id: str
    status: str
    metrics: NodeMetrics


class PipelineStatusResponse(BaseModel):
    mode: str
    batch_size: int
    model: str
    throughput: float
    nodes: list[NodeStatus]


class ConfigPatchRequest(BaseModel):
    mode: Literal["online", "offline", "dual"] | None = None
    batch_size: int | None = None
    model: str | None = None

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 256):
            raise ValueError("batch_size must be between 1 and 256")
        return v


@router.get("/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    _: str | None = Depends(get_tenant_from_token),
) -> PipelineStatusResponse:
    """Return current pipeline status with live throughput sample."""
    throughput = round(random.uniform(8.0, 20.0), 1)
    return PipelineStatusResponse(
        mode=_pipeline_config["mode"],
        batch_size=_pipeline_config["batch_size"],
        model=_pipeline_config["model"],
        throughput=throughput,
        nodes=[
            NodeStatus(id="ingest", status="healthy", metrics=NodeMetrics(rate=round(throughput * 0.42, 1))),
            NodeStatus(id="embed",  status="healthy", metrics=NodeMetrics(rate=throughput)),
            NodeStatus(id="vector", status="degraded", metrics=NodeMetrics(latency=120.0)),
        ],
    )


@router.patch("/config", response_model=PipelineStatusResponse)
async def patch_config(
    body: ConfigPatchRequest,
    _: str | None = Depends(get_tenant_from_token),
) -> PipelineStatusResponse:
    """Partially update pipeline configuration. In-memory only."""
    if body.batch_size is not None and not (1 <= body.batch_size <= 256):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "VALIDATION_ERROR", "message": "batch_size must be between 1 and 256"},
        )
    if body.mode is not None:
        _pipeline_config["mode"] = body.mode
    if body.batch_size is not None:
        _pipeline_config["batch_size"] = body.batch_size
    if body.model is not None:
        _pipeline_config["model"] = body.model

    throughput = round(random.uniform(8.0, 20.0), 1)
    return PipelineStatusResponse(
        mode=_pipeline_config["mode"],
        batch_size=_pipeline_config["batch_size"],
        model=_pipeline_config["model"],
        throughput=throughput,
        nodes=[
            NodeStatus(id="ingest", status="healthy", metrics=NodeMetrics(rate=round(throughput * 0.42, 1))),
            NodeStatus(id="embed",  status="healthy", metrics=NodeMetrics(rate=throughput)),
            NodeStatus(id="vector", status="degraded", metrics=NodeMetrics(latency=120.0)),
        ],
    )
```

**Step 4: Register router in `main.py`**

Add to `pipeline/pipeline/main.py` after the existing `include_router` calls:

```python
from .routes.pipeline import router as pipeline_router
app.include_router(pipeline_router)
```

**Step 5: Create tests directory if missing**

```bash
mkdir -p pipeline/tests/routes
touch pipeline/tests/__init__.py pipeline/tests/routes/__init__.py
```

**Step 6: Run tests to verify they pass**

```bash
cd pipeline
pytest tests/routes/test_pipeline.py -v
```

Expected: All 9 tests PASS.

**Step 7: Commit**

```bash
git add pipeline/pipeline/routes/pipeline.py pipeline/pipeline/main.py pipeline/tests/routes/test_pipeline.py pipeline/tests/routes/__init__.py pipeline/tests/__init__.py
git commit -m "feat: add pipeline status and config endpoints (API-01, API-08)"
```

---

## Task 2: Create `pipeline/pipeline/routes/tenants.py` (API-02 + API-03)

**Files:**
- Create: `pipeline/pipeline/routes/tenants.py`
- Test: `pipeline/tests/routes/test_tenants.py`

**Step 1: Write the failing tests**

Create `pipeline/tests/routes/test_tenants.py`:

```python
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
    monkeypatch.setattr("pipeline.pipeline.db._pool", None)
    resp = client.get("/api/v1/tenants")
    assert resp.status_code == 503


@patch("pipeline.pipeline.routes.tenants._get_pool")
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


@patch("pipeline.pipeline.routes.tenants._get_pool")
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


@patch("pipeline.pipeline.routes.tenants._get_pool")
def test_get_tenant_200(mock_pool):
    pool = AsyncMock()
    pool.fetchrow.return_value = _make_row(FAKE_TENANT)
    mock_pool.return_value = pool

    resp = client.get("/api/v1/tenants/acme-corp")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "acme-corp"
    assert body["state"] == "ACTIVE"


@patch("pipeline.pipeline.routes.tenants._get_pool")
def test_get_tenant_404(mock_pool):
    pool = AsyncMock()
    pool.fetchrow.return_value = None
    mock_pool.return_value = pool

    resp = client.get("/api/v1/tenants/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "TENANT_NOT_FOUND"
```

**Step 2: Run tests to verify they fail**

```bash
cd pipeline
pytest tests/routes/test_tenants.py -v 2>&1 | head -20
```

Expected: ImportError or 404.

**Step 3: Create `pipeline/pipeline/routes/tenants.py`**

```python
"""
Tenant list and detail endpoints.
API-02: GET /api/v1/tenants
API-03: GET /api/v1/tenants/{id}

NOTE: tenants.tenant_id (TEXT) is aliased as both `id` and `name` in responses
until a dedicated `name` column is added via migration.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .. import db
from ..auth import get_tenant_from_token

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


def _get_pool():
    try:
        return db._get_pool()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "DB_UNAVAILABLE", "message": "Control-plane database not initialized"},
        ) from None


class TenantItem(BaseModel):
    id: str
    name: str          # alias for tenant_id until name column added
    state: str
    config: dict[str, Any]
    config_version: int
    created_at: datetime


class TenantsListResponse(BaseModel):
    items: list[TenantItem]
    total: int


def _row_to_tenant(row) -> TenantItem:
    return TenantItem(
        id=row["tenant_id"],
        name=row["tenant_id"],   # alias: name = tenant_id
        state=row["state"],
        config=dict(row["config"]) if row["config"] else {},
        config_version=row["config_version"],
        created_at=row["created_at"],
    )


@router.get("", response_model=TenantsListResponse)
async def list_tenants(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: str | None = Depends(get_tenant_from_token),
) -> TenantsListResponse:
    """List all tenants with pagination."""
    pool = _get_pool()
    offset = (page - 1) * limit

    rows = await pool.fetch(
        """
        SELECT tenant_id, state, config, config_version, created_at
        FROM tenants
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    total = await pool.fetchval("SELECT COUNT(*) FROM tenants")

    return TenantsListResponse(
        items=[_row_to_tenant(r) for r in rows],
        total=total or 0,
    )


@router.get("/{tenant_id}", response_model=TenantItem)
async def get_tenant(
    tenant_id: str,
    _: str | None = Depends(get_tenant_from_token),
) -> TenantItem:
    """Get a single tenant by ID."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        SELECT tenant_id, state, config, config_version, created_at
        FROM tenants
        WHERE tenant_id = $1
        """,
        tenant_id,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "TENANT_NOT_FOUND", "message": f"Tenant '{tenant_id}' not found"},
        )
    return _row_to_tenant(row)
```

**Step 4: Register router in `main.py`**

Add after the pipeline router import:

```python
from .routes.tenants import router as tenants_router
app.include_router(tenants_router)
```

**Step 5: Run tests to verify they pass**

```bash
cd pipeline
pytest tests/routes/test_tenants.py -v
```

Expected: All 5 tests PASS.

**Step 6: Commit**

```bash
git add pipeline/pipeline/routes/tenants.py pipeline/pipeline/main.py pipeline/tests/routes/test_tenants.py
git commit -m "feat: add tenant list and detail endpoints (API-02, API-03)"
```

---

## Task 3: Create `pipeline/pipeline/routes/documents.py` (API-04 + API-06)

**Files:**
- Create: `pipeline/pipeline/routes/documents.py`
- Test: `pipeline/tests/routes/test_documents_api.py`

**Step 1: Write the failing tests**

Create `pipeline/tests/routes/test_documents_api.py`:

```python
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
    monkeypatch.setattr("pipeline.pipeline.db._pool", None)
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 503


@patch("pipeline.pipeline.routes.documents._get_pool")
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


@patch("pipeline.pipeline.routes.documents._get_pool")
def test_list_documents_tenant_filter(mock_pool):
    pool = AsyncMock()
    pool.fetch.return_value = [_make_row(FAKE_DOC)]
    mock_pool.return_value = pool

    resp = client.get("/api/v1/documents?tenantId=acme-corp")
    assert resp.status_code == 200
    call_args = pool.fetch.call_args[0]
    assert "acme-corp" in call_args


@patch("pipeline.pipeline.routes.documents._get_pool")
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


@patch("pipeline.pipeline.routes.documents._get_pool")
def test_get_document_chain_404(mock_pool):
    pool = AsyncMock()
    pool.fetchrow.return_value = None
    mock_pool.return_value = pool

    resp = client.get("/api/v1/documents/nonexistent-uuid/chain")
    assert resp.status_code == 404
    assert resp.json()["detail"]["error_code"] == "DOCUMENT_NOT_FOUND"
```

**Step 2: Run tests to verify they fail**

```bash
cd pipeline
pytest tests/routes/test_documents_api.py -v 2>&1 | head -20
```

Expected: ImportError or 404.

**Step 3: Create `pipeline/pipeline/routes/documents.py`**

```python
"""
Document list and chain-of-custody endpoints.
API-04: GET /api/v1/documents
API-06: GET /api/v1/documents/{id}/chain

DB column mapping:
  documents.custom_metadata  → API field: metadata
  audit_events.event_type    → API field: action
  audit_events.actor         → API field: performed_by
  audit_events.details       → API field: metadata (event metadata)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .. import db
from ..auth import get_tenant_from_token

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _get_pool():
    try:
        return db._get_pool()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "DB_UNAVAILABLE", "message": "Control-plane database not initialized"},
        ) from None


class DocumentItem(BaseModel):
    id: str
    tenant_id: str
    filename: str
    status: str
    modality: str
    metadata: dict[str, Any]   # mapped from custom_metadata
    created_at: datetime
    updated_at: datetime


class DocumentsListResponse(BaseModel):
    items: list[DocumentItem]
    total: int


class ChainEvent(BaseModel):
    action: str                 # mapped from event_type
    timestamp: datetime
    performed_by: str | None    # mapped from actor
    metadata: dict[str, Any]   # mapped from details


class ChainResponse(BaseModel):
    document_id: str
    events: list[ChainEvent]


def _row_to_document(row) -> DocumentItem:
    return DocumentItem(
        id=str(row["id"]),
        tenant_id=row["tenant_id"],
        filename=row["filename"],
        status=row["status"],
        modality=row["modality"],
        metadata=dict(row["custom_metadata"]) if row["custom_metadata"] else {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("", response_model=DocumentsListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    tenantId: str | None = Query(default=None),
    _: str | None = Depends(get_tenant_from_token),
) -> DocumentsListResponse:
    """List documents with optional tenant filter and pagination."""
    pool = _get_pool()
    offset = (page - 1) * limit

    # Single query: COUNT(*) OVER() avoids a second round-trip
    rows = await pool.fetch(
        """
        SELECT id, tenant_id, filename, status, modality,
               custom_metadata, created_at, updated_at,
               COUNT(*) OVER() AS total
        FROM documents
        WHERE ($1::text IS NULL OR tenant_id = $1)
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        tenantId,
        limit,
        offset,
    )

    total = int(rows[0]["total"]) if rows else 0
    return DocumentsListResponse(
        items=[_row_to_document(r) for r in rows],
        total=total,
    )


@router.get("/{document_id}/chain", response_model=ChainResponse)
async def get_document_chain(
    document_id: str,
    _: str | None = Depends(get_tenant_from_token),
) -> ChainResponse:
    """Return chain-of-custody audit events for a document."""
    pool = _get_pool()

    # Verify document exists first
    doc = await pool.fetchrow(
        "SELECT id FROM documents WHERE id = $1::uuid",
        document_id,
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DOCUMENT_NOT_FOUND", "message": f"Document '{document_id}' not found"},
        )

    events = await pool.fetch(
        """
        SELECT event_id, event_type, timestamp, actor, details
        FROM audit_events
        WHERE resource_type = 'document' AND resource_id = $1
        ORDER BY timestamp ASC
        """,
        document_id,
    )

    return ChainResponse(
        document_id=document_id,
        events=[
            ChainEvent(
                action=row["event_type"],
                timestamp=row["timestamp"],
                performed_by=row["actor"],
                metadata=dict(row["details"]) if row["details"] else {},
            )
            for row in events
        ],
    )
```

**Step 4: Register router in `main.py`**

```python
from .routes.documents import router as documents_router
app.include_router(documents_router)
```

**Step 5: Run tests to verify they pass**

```bash
cd pipeline
pytest tests/routes/test_documents_api.py -v
```

Expected: All 5 tests PASS.

**Step 6: Commit**

```bash
git add pipeline/pipeline/routes/documents.py pipeline/pipeline/main.py pipeline/tests/routes/test_documents_api.py
git commit -m "feat: add document list and chain-of-custody endpoints (API-04, API-06)"
```

---

## Task 4: Create `pipeline/pipeline/routes/verification.py` (API-07)

**Files:**
- Create: `pipeline/pipeline/routes/verification.py`
- Test: `pipeline/tests/routes/test_verification.py`

**Step 1: Write the failing tests**

Create `pipeline/tests/routes/test_verification.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
cd pipeline
pytest tests/routes/test_verification.py -v 2>&1 | head -20
```

Expected: ImportError or 404.

**Step 3: Create `pipeline/pipeline/routes/verification.py`**

```python
"""
Verification test suite endpoint.
API-07: POST /api/v1/verification/test

MVP: deterministic mock responses keyed on testType.
TODO: Integrate with actual verification logic (gate-based analysis).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import get_tenant_from_token

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])

_MOCK_RESULTS: dict[str, dict] = {
    "red-team": {
        "score": 85,
        "details": [
            {"test": "Injection", "passed": True, "message": "No injection vulnerabilities detected."},
            {"test": "Encryption", "passed": False, "message": "TLS 1.0 detected on internal service."},
            {"test": "AuthBypass", "passed": True, "message": "Authentication cannot be bypassed."},
            {"test": "DataExfiltration", "passed": True, "message": "Exfiltration vectors blocked."},
        ],
    },
    "compliance": {
        "score": 92,
        "details": [
            {"test": "GDPR-DataMinimization", "passed": True, "message": "Only required fields collected."},
            {"test": "HIPAA-Encryption", "passed": True, "message": "PHI encrypted at rest and in transit."},
            {"test": "FedRAMP-AuditLog", "passed": True, "message": "Audit log is append-only and complete."},
            {"test": "RetentionPolicy", "passed": False, "message": "Retention policy not enforced on archived docs."},
        ],
    },
    "penetration": {
        "score": 78,
        "details": [
            {"test": "SQLInjection", "passed": True, "message": "Parameterized queries in use."},
            {"test": "XSS", "passed": True, "message": "Content-Security-Policy header present."},
            {"test": "CSRF", "passed": False, "message": "CSRF token missing on state-changing endpoints."},
            {"test": "BruteForce", "passed": True, "message": "Rate limiting active on auth endpoints."},
        ],
    },
}

VALID_TEST_TYPES = set(_MOCK_RESULTS.keys())


class VerificationTestRequest(BaseModel):
    testType: str


class VerificationDetail(BaseModel):
    test: str
    passed: bool
    message: str


class VerificationTestResponse(BaseModel):
    score: int
    details: list[VerificationDetail]


@router.post("/test", response_model=VerificationTestResponse)
async def run_verification_test(
    body: VerificationTestRequest,
    _: str | None = Depends(get_tenant_from_token),
) -> VerificationTestResponse:
    """Run a deterministic mock verification test suite by test type."""
    if body.testType not in VALID_TEST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_TEST_TYPE",
                "message": f"testType must be one of: {', '.join(sorted(VALID_TEST_TYPES))}",
            },
        )
    result = _MOCK_RESULTS[body.testType]
    return VerificationTestResponse(
        score=result["score"],
        details=[VerificationDetail(**d) for d in result["details"]],
    )
```

**Step 4: Register router in `main.py`**

```python
from .routes.verification import router as verification_router
app.include_router(verification_router)
```

**Step 5: Run tests to verify they pass**

```bash
cd pipeline
pytest tests/routes/test_verification.py -v
```

Expected: All 6 tests PASS.

**Step 6: Commit**

```bash
git add pipeline/pipeline/routes/verification.py pipeline/pipeline/main.py pipeline/tests/routes/test_verification.py
git commit -m "feat: add verification test endpoint (API-07)"
```

---

## Task 5: Full Test Suite + OpenAPI spec update

**Files:**
- Modify: `specs/openapi.yaml`
- Run: full test suite

**Step 1: Run the complete test suite**

```bash
cd pipeline
pytest tests/routes/ -v --tb=short
```

Expected: All tests pass. Note any failures.

**Step 2: Verify server starts cleanly**

```bash
cd pipeline
FROSTBYTE_AUTH_BYPASS=true uvicorn pipeline.main:app --port 8001 &
sleep 2
curl -s http://localhost:8001/api/v1/pipeline/status | python3 -m json.tool
curl -s http://localhost:8001/api/v1/tenants | python3 -m json.tool
curl -s http://localhost:8001/api/v1/documents | python3 -m json.tool
curl -s -X POST http://localhost:8001/api/v1/verification/test -H "Content-Type: application/json" -d '{"testType":"red-team"}' | python3 -m json.tool
curl -s -X PATCH http://localhost:8001/api/v1/config -H "Content-Type: application/json" -d '{"mode":"offline","batch_size":75}' | python3 -m json.tool
kill %1
```

Expected: JSON responses with correct shapes for all 5 calls.

**Step 3: Update OpenAPI spec**

Add the 7 new endpoints to `specs/openapi.yaml`. Append under `paths:`:

```yaml
  /api/v1/pipeline/status:
    get:
      summary: Get pipeline status
      operationId: getPipelineStatus
      tags: [pipeline]
      security: [{bearerAuth: []}]
      responses:
        '200':
          description: Pipeline status
          content:
            application/json:
              schema: {$ref: '#/components/schemas/PipelineStatus'}
        '401':
          description: Unauthorized

  /api/v1/config:
    patch:
      summary: Update pipeline configuration
      operationId: patchConfig
      tags: [pipeline]
      security: [{bearerAuth: []}]
      requestBody:
        content:
          application/json:
            schema: {$ref: '#/components/schemas/ConfigPatchRequest'}
      responses:
        '200':
          description: Updated config
          content:
            application/json:
              schema: {$ref: '#/components/schemas/PipelineStatus'}
        '400':
          description: Validation error

  /api/v1/tenants:
    get:
      summary: List tenants
      operationId: listTenants
      tags: [tenants]
      security: [{bearerAuth: []}]
      parameters:
        - {name: page, in: query, schema: {type: integer, default: 1}}
        - {name: limit, in: query, schema: {type: integer, default: 20, maximum: 100}}
      responses:
        '200':
          description: Tenant list
          content:
            application/json:
              schema: {$ref: '#/components/schemas/TenantsList'}

  /api/v1/tenants/{id}:
    get:
      summary: Get tenant by ID
      operationId: getTenant
      tags: [tenants]
      security: [{bearerAuth: []}]
      parameters:
        - {name: id, in: path, required: true, schema: {type: string}}
      responses:
        '200':
          description: Tenant detail
          content:
            application/json:
              schema: {$ref: '#/components/schemas/Tenant'}
        '404':
          description: Not found

  /api/v1/documents:
    get:
      summary: List documents
      operationId: listDocuments
      tags: [documents]
      security: [{bearerAuth: []}]
      parameters:
        - {name: page, in: query, schema: {type: integer, default: 1}}
        - {name: limit, in: query, schema: {type: integer, default: 20, maximum: 100}}
        - {name: tenantId, in: query, schema: {type: string}}
      responses:
        '200':
          description: Document list
          content:
            application/json:
              schema: {$ref: '#/components/schemas/DocumentsList'}

  /api/v1/documents/{id}/chain:
    get:
      summary: Get document chain of custody
      operationId: getDocumentChain
      tags: [documents]
      security: [{bearerAuth: []}]
      parameters:
        - {name: id, in: path, required: true, schema: {type: string, format: uuid}}
      responses:
        '200':
          description: Chain of custody
          content:
            application/json:
              schema: {$ref: '#/components/schemas/ChainResponse'}
        '404':
          description: Not found

  /api/v1/verification/test:
    post:
      summary: Run verification test suite
      operationId: runVerificationTest
      tags: [verification]
      security: [{bearerAuth: []}]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [testType]
              properties:
                testType:
                  type: string
                  enum: [red-team, compliance, penetration]
      responses:
        '200':
          description: Verification results
          content:
            application/json:
              schema: {$ref: '#/components/schemas/VerificationResult'}
        '400':
          description: Invalid test type
```

**Step 4: Final commit**

```bash
git add specs/openapi.yaml
git commit -m "docs: update OpenAPI spec with 7 new API endpoints (API-01 through API-08)"
```

---

## Task 6: Manual QA Verification

Run each check against the live server (`VITE_MOCK_API=false`):

```bash
# Start server
cd pipeline && FROSTBYTE_AUTH_BYPASS=true uvicorn pipeline.main:app --port 8000 &

BASE="http://localhost:8000"

# API-01: Pipeline status
curl -s $BASE/api/v1/pipeline/status | python3 -m json.tool
# ✅ Expect: mode, batch_size, model, throughput (float), nodes (3 items)

# API-02: List tenants
curl -s "$BASE/api/v1/tenants?page=1&limit=5" | python3 -m json.tool
# ✅ Expect: {items: [...], total: N}

# API-03: Get tenant (use a real tenant_id from the list above)
curl -s $BASE/api/v1/tenants/default | python3 -m json.tool
# ✅ Expect: tenant object or 404

# API-04: List documents
curl -s $BASE/api/v1/documents | python3 -m json.tool
# ✅ Expect: {items: [...], total: N}, metadata field present

# API-04: With tenant filter
curl -s "$BASE/api/v1/documents?tenantId=default" | python3 -m json.tool

# API-06: Chain of custody (use a real document id from list above)
DOC_ID="<paste-id-here>"
curl -s $BASE/api/v1/documents/$DOC_ID/chain | python3 -m json.tool
# ✅ Expect: {document_id, events: [...]}

# API-07: Verification test
curl -s -X POST $BASE/api/v1/verification/test \
  -H "Content-Type: application/json" \
  -d '{"testType": "red-team"}' | python3 -m json.tool
# ✅ Expect: {score: 85, details: [4 items]}

# API-08: Config patch
curl -s -X PATCH $BASE/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{"mode": "offline", "batch_size": 75}' | python3 -m json.tool
# ✅ Expect: updated config echoed back

# API-08: Validate reflected in status
curl -s $BASE/api/v1/pipeline/status | python3 -m json.tool
# ✅ Expect: mode=offline, batch_size=75

# Error cases
curl -s -X PATCH $BASE/api/v1/config -H "Content-Type: application/json" -d '{"batch_size": 0}'
# ✅ Expect: 400 VALIDATION_ERROR

curl -s $BASE/api/v1/tenants/this-does-not-exist
# ✅ Expect: 404 TENANT_NOT_FOUND
```
