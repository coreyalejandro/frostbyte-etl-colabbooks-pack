# Prompt: Implement Missing Backend APIs for Frostbyte ETL Dashboard

You are an expert backend engineer tasked with completing the Frostbyte ETL Dashboard by implementing the missing backend API endpoints. All frontend work is done; the dashboard client already contains stubs for these endpoints (in `src/api/client.ts`) and uses mock data when `VITE_MOCK_API=true`. Your job is to replace the mocks with real implementations in the `packages/api` service.

### Context
- **Repository**: `https://github.com/coreyalejandro/frostbyte-etl-colabbooks-pack`
- **Backend framework**: FastAPI (async)
- **Database**: PostgreSQL with `pgvector` extension
- **Database driver**: `asyncpg`
- **Existing endpoints**: 
  - `GET /health` – implemented
  - `GET /documents/{id}` – implemented (API-05)
  - `GET /tenants/{id}/schema` – implemented (API-09)
  - `POST /auth/token` – implemented (API-11)
  - `GET /intake`, `POST /intake` – implemented but not wired in UI (API-12)
- **Dashboard client expectations**: All endpoints return JSON with consistent error format: `{"error_code": string, "message": string}` and appropriate HTTP status codes (400, 401, 403, 404, 409, 500).

The **Verification & Completion Plan (v3.0)** audited on 2026-02-17 states that the following backend endpoints are **missing** and must be implemented now for production readiness:

| ID | Endpoint | Method | Purpose |
|----|----------|--------|---------|
| API-01 | `/api/v1/pipeline/status` | GET | Return current pipeline status (mode, batch size, model, throughput metrics, node statuses). |
| API-02 | `/api/v1/tenants` | GET | List all tenants with pagination (`page`, `limit`). |
| API-03 | `/api/v1/tenants/{id}` | GET | Get details of a single tenant (including its configuration). |
| API-04 | `/api/v1/documents` | GET | List all documents (with optional `tenantId` filter) with pagination. |
| API-06 | `/api/v1/documents/{id}/chain` | GET | Return the chain‑of‑custody for a document (list of events: created, verified, etc.). |
| API-07 | `/api/v1/verification/test` | POST | Run a verification test suite (accepts `testType` in body, returns security score and details). |
| API-08 | `/api/v1/config` | PATCH | Update pipeline configuration (mode, batch size, model). |

### Requirements for Each Endpoint

#### General
- All endpoints **must** be prefixed with `/api/v1` (the existing code may already mount routers accordingly).
- Use `async` functions.
- Authentication: The dashboard sends a Bearer token (JWT) obtained from `/auth/token`. Validate the token and extract `tenant_id` from the `sub` claim (or use a dependency like `get_current_user`). For endpoints that are tenant‑scoped, ensure the user has access to that tenant.
- Pagination: Accept `page` (int, default 1) and `limit` (int, default 20, max 100) query parameters. Return a JSON object with `items` and `total`.
- Error handling: Raise `HTTPException` with appropriate status code and detail (use the `Error` schema defined in OpenAPI).

#### Database Schema Assumptions (from existing migrations)
```sql
-- tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- audit_log (for chain of custody)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    action TEXT NOT NULL, -- e.g., 'CREATED', 'VERIFIED', 'DELETED'
    performed_by UUID, -- user id if available
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### Detailed Endpoint Specifications

##### 1. `GET /api/v1/pipeline/status`
- **Response body** (example):
```json
{
  "mode": "dual",
  "batch_size": 50,
  "model": "nomic-embed-text-v1.5",
  "throughput": 12.4,
  "nodes": [
    { "id": "ingest", "status": "healthy", "metrics": { "rate": 5.2 } },
    { "id": "embed", "status": "healthy", "metrics": { "rate": 12.4 } },
    { "id": "vector", "status": "degraded", "metrics": { "latency": 120 } }
  ]
}
```
- Implementation: This can be either a real aggregation from services or a static/mock response for now (but should be plausible). For MVP, you may return a static status with random throughput.

##### 2. `GET /api/v1/tenants`
- Query params: `page`, `limit`
- Response:
```json
{
  "items": [
    { "id": "uuid", "name": "Acme Corp", "config": {}, "created_at": "..." }
  ],
  "total": 42
}
```
- SQL: `SELECT id, name, config, created_at FROM tenants ORDER BY created_at DESC LIMIT $1 OFFSET $2`

##### 3. `GET /api/v1/tenants/{id}`
- Path param: `id` (UUID)
- Response: single tenant object (as above) or 404.
- Also include any computed fields like `document_count`? Not required but can be added.

##### 4. `GET /api/v1/documents`
- Query params: `page`, `limit`, `tenantId` (optional UUID)
- Response:
```json
{
  "items": [
    { "id": "uuid", "tenant_id": "uuid", "filename": "doc.pdf", "status": "completed", "created_at": "...", "updated_at": "..." }
  ],
  "total": 123
}
```
- SQL: Build query dynamically with optional tenant filter.

##### 5. `GET /api/v1/documents/{id}/chain`
- Path param: `id` (UUID)
- Response:
```json
{
  "document_id": "uuid",
  "events": [
    { "action": "CREATED", "timestamp": "2026-02-17T10:00:00Z", "performed_by": "user@example.com", "metadata": {} },
    { "action": "VERIFIED", "timestamp": "2026-02-17T10:05:00Z", "performed_by": "verifier@example.com", "metadata": { "hash": "abc123" } }
  ]
}
```
- SQL: Query `audit_log` for the document, join with users if needed.

##### 6. `POST /api/v1/verification/test`
- Request body:
```json
{
  "testType": "red-team"  // could be "red-team", "compliance", etc.
}
```
- Response:
```json
{
  "score": 85,
  "details": [
    { "test": "Injection", "passed": true, "message": "No vulnerabilities found." },
    { "test": "Encryption", "passed": false, "message": "TLS 1.0 detected." }
  ]
}
```
- Implementation: For MVP, return a deterministic mock based on `testType`. Later, integrate with actual verification logic.

##### 7. `PATCH /api/v1/config`
- Request body (partial update):
```json
{
  "mode": "offline",      // optional
  "batch_size": 75,       // optional (must be 1-256)
  "model": "nomic-embed-text-v1.5" // optional
}
```
- Response: updated full config (as in `pipeline/status` maybe).
- Store config in a global settings table or in tenant config? The dashboard is not tenant‑specific for this config. Assume a single global config stored in a `pipeline_config` table or in environment variables. For now, store in memory (not persistent) but implement a simple in‑memory store.

### Implementation Plan
1. Create new router files in `packages/api/routers/` (or extend existing ones). Follow the pattern of `documents.py`.
2. Add the endpoints with proper dependencies (authentication, database connection).
3. Write SQL queries using `asyncpg`.
4. Ensure all endpoints handle 404 and validation errors.
5. Update the OpenAPI spec (`specs/openapi.yaml`) to include these endpoints (if not already there). The spec currently covers only basic endpoints; you may add these.
6. Test manually using `curl` or the dashboard in non‑mock mode (`VITE_MOCK_API=false`).

### Output
Provide the complete code for each endpoint, including:
- File paths (relative to `packages/api/`)
- Import statements
- Pydantic models for request/response
- Router definitions
- Any necessary database queries

Also include a short verification checklist (in Markdown) that QA can use to test these endpoints manually.

**Important**: Do not include any ambiguous words like "maybe", "could", "might". All instructions are commands. Use imperative mood. The code must be production‑ready, with proper error handling and comments.

Now, execute the plan.