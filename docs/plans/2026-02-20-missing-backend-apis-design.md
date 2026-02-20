# Design: Missing Backend APIs for Frostbyte ETL Dashboard

**Date:** 2026-02-20
**Status:** Approved
**Audited schema:** 2026-02-17 Verification & Completion Plan v3.0
**Approach:** Option A — implement against real existing migrations, no new migrations required

---

## Context

The Frostbyte ETL Dashboard frontend is complete and uses mock data when `VITE_MOCK_API=true`. Seven backend endpoints are missing. This design implements them in `pipeline/pipeline/routes/` following the established FastAPI/asyncpg patterns.

## Real Database Schema (confirmed from migrations)

| Table | Key Columns |
|---|---|
| `tenants` | `tenant_id TEXT PK`, `state TEXT`, `config JSONB`, `config_version INT`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ` |
| `documents` | `id UUID PK`, `tenant_id TEXT`, `filename TEXT`, `status TEXT`, `modality TEXT`, `custom_metadata JSONB`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ` |
| `audit_events` | `event_id UUID PK`, `tenant_id TEXT`, `event_type TEXT`, `timestamp TIMESTAMPTZ`, `actor TEXT`, `resource_type TEXT`, `resource_id TEXT`, `details JSONB` |

**Column name aliases required (DB → API):**
- `tenants.tenant_id` → `id` and `name` (alias until name column added)
- `documents.custom_metadata` → `metadata`
- `audit_events.event_type` → `action`
- `audit_events.timestamp` → `timestamp`
- `audit_events.actor` → `performed_by`
- `audit_events.details` → `metadata`

---

## Architecture

Four new router files added to `pipeline/pipeline/routes/`. All registered in `main.py`. No other structural changes.

```
pipeline/pipeline/routes/
  pipeline.py       ← API-01 (GET /pipeline/status), API-08 (PATCH /config)
  tenants.py        ← API-02 (GET /tenants), API-03 (GET /tenants/{id})
  documents.py      ← API-04 (GET /documents), API-06 (GET /documents/{id}/chain)
  verification.py   ← API-07 (POST /verification/test)
```

---

## Endpoint Specifications

### API-01: `GET /api/v1/pipeline/status`

**Purpose:** Return current pipeline status.
**Auth:** Required (Bearer JWT).
**DB:** None — static response driven by in-memory `_pipeline_config` dict.
**Response:**
```json
{
  "mode": "dual",
  "batch_size": 50,
  "model": "nomic-embed-text-v1.5",
  "throughput": 12.4,
  "nodes": [
    {"id": "ingest", "status": "healthy", "metrics": {"rate": 5.2}},
    {"id": "embed",  "status": "healthy", "metrics": {"rate": 12.4}},
    {"id": "vector", "status": "degraded", "metrics": {"latency": 120}}
  ]
}
```
**Implementation note:** `throughput` is `random.uniform(8.0, 20.0)` rounded to 1 decimal. Node statuses are static for MVP.

---

### API-02: `GET /api/v1/tenants`

**Purpose:** List all tenants with pagination.
**Auth:** Required. Admin token (`sub=admin`) sees all; tenant token sees only own record.
**Query params:** `page: int = 1`, `limit: int = 20` (max 100).
**SQL:**
```sql
SELECT tenant_id, state, config, config_version, created_at
FROM tenants
ORDER BY created_at DESC
LIMIT $1 OFFSET $2
```
```sql
SELECT COUNT(*) FROM tenants
```
**Response:** `{"items": [...], "total": N}`
**Field mapping:** `tenant_id → id`, `tenant_id → name` (documented alias, see caveats).

---

### API-03: `GET /api/v1/tenants/{id}`

**Purpose:** Get single tenant detail.
**Auth:** Required.
**SQL:**
```sql
SELECT tenant_id, state, config, config_version, created_at
FROM tenants
WHERE tenant_id = $1
```
**Errors:** 404 `TENANT_NOT_FOUND` if no row.

---

### API-04: `GET /api/v1/documents`

**Purpose:** List documents with optional tenant filter and pagination.
**Auth:** Required. Non-admin tokens are implicitly scoped to their `tenant_id`.
**Query params:** `page: int = 1`, `limit: int = 20` (max 100), `tenantId: str | None`.
**SQL (with filter):**
```sql
SELECT id, tenant_id, filename, status, modality, custom_metadata, created_at, updated_at,
       COUNT(*) OVER() AS total
FROM documents
WHERE ($1::text IS NULL OR tenant_id = $1)
ORDER BY created_at DESC
LIMIT $2 OFFSET $3
```
**Response:** `{"items": [...], "total": N}`
**Field mapping:** `custom_metadata → metadata`.

---

### API-06: `GET /api/v1/documents/{id}/chain`

**Purpose:** Return chain-of-custody events for a document.
**Auth:** Required.
**SQL:**
```sql
SELECT event_id, event_type, timestamp, actor, details
FROM audit_events
WHERE resource_type = 'document' AND resource_id = $1
ORDER BY timestamp ASC
```
**Response:**
```json
{
  "document_id": "uuid",
  "events": [
    {"action": "DOCUMENT_INGESTED", "timestamp": "...", "performed_by": "system", "metadata": {}}
  ]
}
```
**Errors:** 404 `DOCUMENT_NOT_FOUND` if document does not exist in `documents` table (verified first).

---

### API-07: `POST /api/v1/verification/test`

**Purpose:** Run a deterministic mock verification test suite.
**Auth:** Required.
**Body:** `{"testType": "red-team" | "compliance" | "penetration"}`
**DB:** None — deterministic mock keyed on `testType`.
**Response:**
```json
{
  "score": 85,
  "details": [
    {"test": "Injection", "passed": true, "message": "No vulnerabilities found."},
    {"test": "Encryption", "passed": false, "message": "TLS 1.0 detected."}
  ]
}
```
**TODO (post-MVP):** Integrate with actual verification logic.

---

### API-08: `PATCH /api/v1/config`

**Purpose:** Update pipeline configuration.
**Auth:** Required.
**Body (all fields optional):**
```json
{"mode": "offline", "batch_size": 75, "model": "nomic-embed-text-v1.5"}
```
**Validation:** `batch_size` must be 1–256. `mode` must be `"online"`, `"offline"`, or `"dual"`.
**DB:** None — updates module-level `_pipeline_config` dict in `pipeline.py`.
**Response:** Full updated config (same shape as API-01).
**Caveat:** In-memory only. Config does not survive process restart and will diverge under horizontal scaling.
**TODO:** Persist config to a `pipeline_config` table in a future migration.

---

## Authentication Pattern

All endpoints use:
```python
current_user: str | None = Depends(get_tenant_from_token)
```
- `FROSTBYTE_AUTH_BYPASS=true` → no token required, `current_user = None`
- `sub=admin` → admin scope, can see all tenants/documents
- `sub=<tenant_id>` → tenant-scoped, filtered automatically

---

## Error Response Format

All errors follow the established pattern:
```python
raise HTTPException(
    status_code=404,
    detail={"error_code": "NOT_FOUND", "message": "Tenant not found"}
)
```

Standard codes used:
| Status | `error_code` |
|---|---|
| 400 | `VALIDATION_ERROR` |
| 401 | `AUTHENTICATION_REQUIRED` |
| 403 | `INSUFFICIENT_PERMISSIONS` |
| 404 | `NOT_FOUND` / `TENANT_NOT_FOUND` / `DOCUMENT_NOT_FOUND` |
| 503 | `DB_UNAVAILABLE` |

---

## `main.py` Changes

Four `include_router` calls added after existing routers:
```python
from .routes.pipeline import router as pipeline_router
from .routes.tenants import router as tenants_router
from .routes.documents import router as documents_router
from .routes.verification import router as verification_router

app.include_router(pipeline_router)
app.include_router(tenants_router)
app.include_router(documents_router)
app.include_router(verification_router)
```

---

## QA Verification Checklist

```markdown
### API-01 Pipeline Status
- [ ] GET /api/v1/pipeline/status → 200 with mode, batch_size, model, throughput, nodes
- [ ] throughput is a float (varies each call)
- [ ] 401 when no token and AUTH_BYPASS=false

### API-02 List Tenants
- [ ] GET /api/v1/tenants → 200 with items array and total
- [ ] GET /api/v1/tenants?page=2&limit=5 → correct offset
- [ ] limit > 100 → clamped to 100 or 422

### API-03 Get Tenant
- [ ] GET /api/v1/tenants/{valid_id} → 200 with tenant object
- [ ] GET /api/v1/tenants/nonexistent → 404 with error_code TENANT_NOT_FOUND

### API-04 List Documents
- [ ] GET /api/v1/documents → 200 with items and total
- [ ] GET /api/v1/documents?tenantId=xxx → filtered results
- [ ] metadata field present (mapped from custom_metadata)

### API-06 Document Chain
- [ ] GET /api/v1/documents/{id}/chain → 200 with document_id and events array
- [ ] events ordered by timestamp ASC
- [ ] GET /api/v1/documents/nonexistent/chain → 404

### API-07 Verification Test
- [ ] POST /api/v1/verification/test {"testType": "red-team"} → 200 with score and details
- [ ] POST /api/v1/verification/test {"testType": "compliance"} → different deterministic result
- [ ] Missing testType → 422

### API-08 Config Patch
- [ ] PATCH /api/v1/config {"mode": "offline"} → 200 with updated config
- [ ] batch_size: 0 → 400 VALIDATION_ERROR
- [ ] batch_size: 257 → 400 VALIDATION_ERROR
- [ ] GET /api/v1/pipeline/status after PATCH reflects new values
```

---

## Caveats (Documented)

1. **`tenants.name` alias:** `name` field in API response is an alias for `tenant_id` until a `name TEXT` column is added via migration.
2. **In-memory config:** `PATCH /config` state is lost on process restart. Document in ops runbook.
3. **Horizontal scaling:** `_pipeline_config` is per-process. Under multi-worker deployments, config will diverge. Acceptable for MVP.
4. **`audit_events` filter:** Chain-of-custody uses `resource_type='document'` filter. Events emitted by the intake pipeline must use this `resource_type` value for chain to be populated.
