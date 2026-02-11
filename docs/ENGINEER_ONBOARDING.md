# Engineer Onboarding: Frostbyte ETL Pipeline

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** ONBOARD-01, ONBOARD-02, ONBOARD-03  
**References:** [PRD.md](PRD.md), [ARCHITECTURE.md](.planning/research/ARCHITECTURE.md), [BUILD_1HR.md](../BUILD_1HR.md)

---

## 1. Architecture Walkthrough

### 1.1 Three-Tier Model

The Frostbyte pipeline uses a **control plane / data plane / audit plane** separation. Each plane has distinct responsibilities.

```
                    ┌─────────────────────────────────────┐
                    │         CONTROL PLANE (shared)       │
                    │  Tenant Registry, Provisioning       │
                    │  API Gateway, Job Dispatcher         │
                    │  Audit Stream Aggregator             │
                    └──────────────┬──────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  DATA PLANE A   │    │  DATA PLANE B   │    │  DATA PLANE C   │
│  Intake Gateway │    │  Intake Gateway  │    │  Intake Gateway │
│  Parse Workers  │    │  Parse Workers  │    │  Parse Workers  │
│  Policy Engine  │    │  Policy Engine   │    │  Policy Engine  │
│  Embedding Svc  │    │  Embedding Svc   │    │  Embedding Svc  │
│  MinIO, PG,     │    │  MinIO, PG,      │    │  MinIO, PG,     │
│  Qdrant, Redis  │    │  Qdrant, Redis   │    │  Qdrant, Redis  │
│  Serving API    │    │  Serving API     │    │  Serving API    │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    AUDIT PLANE        │
                    │  (append-only,        │
                    │   immutable)          │
                    └───────────────────────┘
```

### 1.2 Control Plane Responsibilities

| Component | Responsibility | Does NOT |
|-----------|----------------|----------|
| **Tenant Registry** | Tenant metadata, state, config, API keys | Touch document content |
| **Provisioning Orchestrator** | Create/destroy per-tenant infra (Hetzner) | Store documents |
| **API Gateway** | TLS, JWT validation, rate limit, tenant routing | Parse or store files |
| **Job Dispatcher** | Route jobs to correct tenant queue | Access document bytes |
| **Audit Stream Aggregator** | Collect events from data planes, write to audit store | Modify or delete audit events |

**Key principle:** A compromise of the control plane does **not** expose document content. It manages identity, routing, and lifecycle only.

### 1.3 Data Plane Responsibilities (Per-Tenant)

| Component | Responsibility |
|-----------|----------------|
| **Intake Gateway** | Trust boundary: validate manifest, MIME, checksum, malware; write raw files; enqueue parse jobs |
| **Parse Workers** | Docling + Unstructured → canonical JSON; layout-aware, chunking |
| **Policy Engine** | PII, classification, injection defense; deterministic chunk IDs |
| **Embedding Service** | OpenRouter (online) or Nomic (offline) → 768d vectors |
| **Object Store (MinIO)** | Raw uploads, normalized JSON, receipts |
| **PostgreSQL** | Governance metadata, lineage, chunk metadata |
| **Qdrant** | Vector embeddings for RAG retrieval |
| **Serving API** | RAG retrieval with retrieval proof, cite-only-from-retrieval |

**Key principle:** Blast radius is limited to one tenant by construction. Tenant A cannot access Tenant B's data.

### 1.4 Audit Plane Responsibilities

| Responsibility | Constraint |
|----------------|------------|
| Append-only store | No UPDATE, no DELETE |
| Event schema | event_id, tenant_id, event_type, timestamp, resource_type, resource_id, details |
| Hash chain | previous_event_id for provenance |
| Query | By tenant, by document, by time range |

**Key principle:** Audit plane is write-only from data planes. Operations and auditors read only.

### 1.5 Self-Check Questions

After this walkthrough, you should be able to answer:

1. What does the control plane **never** touch?
2. What limits blast radius if a data plane component is compromised?
3. Why is the audit plane append-only?
4. How does offline mode differ from online mode at the architecture level?

**Answers:** (1) Document content. (2) Per-tenant isolation; only one tenant's data. (3) Tamper evidence, compliance, provenance chains. (4) Offline collapses data plane into a single Docker stack; control plane → static config; embedding → local Nomic instead of OpenRouter.

---

## 2. Local Development Setup

### 2.1 Prerequisites

| Requirement | Version | Verify |
|-------------|---------|--------|
| Docker | >= 24 | `docker --version` |
| Docker Compose | >= 2.29 | `docker compose version` |
| Python | >= 3.12 | `python3 --version` |
| Optional | — | `curl`, `jq` for API testing |

### 2.2 Step 1: Start Infrastructure (~5 min)

```bash
cd /path/to/frostbyte_etl_colabbooks_pack_2026-02-07

docker compose up -d

# Wait for health (typically 30–60 s)
docker compose ps
# All services should show "healthy"
```

| Service | Port | Purpose |
|---------|------|---------|
| MinIO | 9000, 9001 | Object store |
| PostgreSQL | 5432 | Relational DB |
| Redis | 6379 | Queue, cache |
| Qdrant | 6333 | Vector store |

### 2.3 Step 2: Run Migrations

```bash
# Migrations order: 001 (tenant registry), 002 (audit), then app migrations
# If migrations/ exists:
docker compose exec postgres psql -U postgres -d frostbyte -f /path/to/migrations/001_tenant_registry.sql
# Or use Alembic if configured:
# cd pipeline && alembic upgrade head
```

**Reference:** [FOUNDATION_LAYER_PLAN Section 3.2](FOUNDATION_LAYER_PLAN.md).

### 2.4 Step 3: Install Pipeline and Start API

```bash
cd pipeline
pip install -e .
uvicorn pipeline.main:app --reload --host 0.0.0.0 --port 8000
```

API available at `http://localhost:8000`.

### 2.5 Step 4: Test with Sample Data

**Create a test file:**
```bash
echo "Test document content for Frostbyte ETL pipeline. This is a sample." > /tmp/test-doc.txt
sha256sum /tmp/test-doc.txt
# Use the hash in the manifest sha256 field
```

**Submit a batch (simplified; adjust to actual API):**
```bash
# Example (actual API may differ—see INTAKE_GATEWAY_PLAN for full schema)
curl -X POST http://localhost:8000/api/v1/ingest/default/batch \
  -H "Authorization: Bearer <JWT>" \
  -F 'manifest={"batch_id":"batch_dev_001","tenant_id":"default","file_count":1,"files":[{"file_id":"f1","filename":"test.txt","mime_type":"text/plain","size_bytes":62,"sha256":"<hash>"}]}' \
  -F "files=@/tmp/test-doc.txt"
```

**Verify:**
- MinIO: `mc ls local/frostbyte-docs/` or equivalent
- Qdrant: `curl -s http://localhost:6333/collections | jq`
- Receipt: Check response or GET batch status

### 2.6 Troubleshooting Dev Setup

| Issue | Check |
|-------|-------|
| Services not healthy | `docker compose logs`; ensure ports not in use |
| Migration fails | Verify PostgreSQL is up; check migration order |
| API 401 | JWT required in production; local dev may use bypass (check config) |
| Intake 400 | Manifest schema must match INTAKE_GATEWAY_PLAN; sha256 must match file |

---

## 3. First Task: Add a New Document Type

This guide walks through adding support for a new document format (example: ODS — OpenDocument Spreadsheet) end-to-end, producing a PR-ready changeset.

### 3.1 Task Scope

- Add ODS to MIME allowlist
- Add parser routing for ODS
- Add test coverage
- Document in PRD/allowlist

### 3.2 Step 1: MIME Allowlist

**File:** Refer to [DOCUMENT_SAFETY Section 3](DOCUMENT_SAFETY.md) and tenant config `mime_allowlist`.

**Add:**
```
application/vnd.oasis.opendocument.spreadsheet
```

**Location:** Either (a) default allowlist in config schema (PRD Appendix G), or (b) DOCUMENT_SAFETY Section 3.2 table.

### 3.3 Step 2: Parser Routing

**File:** [PARSING_PIPELINE_PLAN](PARSING_PIPELINE_PLAN.md) — parser selection by MIME type.

**Add route:**
```python
# Pseudo-code; actual implementation in parser router
MIME_TO_PARSER = {
    "application/pdf": "docling",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "unstructured",
    "application/vnd.oasis.opendocument.spreadsheet": "unstructured",  # NEW
    # ...
}
```

**Unstructured** supports ODS via `unstructured[all-docs]`. Verify `partition` behavior for spreadsheets (tables → chunks).

### 3.4 Step 3: Tests

1. **Unit:** Parser returns valid canonical JSON for sample ODS file
2. **Integration:** Intake → parse → policy → embed → store; verify chunk count, lineage
3. **Reject:** Submit ODS without allowlist entry → UNSUPPORTED_FORMAT

### 3.5 Step 4: Documentation

- Update PRD Section 2.1 or Appendix (supported formats)
- Update DOCUMENT_SAFETY MIME table
- Add sample ODS to test fixtures (if not already)

### 3.6 PR Checklist

- [ ] MIME allowlist updated
- [ ] Parser route added
- [ ] Unit + integration tests pass
- [ ] Docs updated
- [ ] No secrets or credentials in diff

---

## 4. Cross-References

| Topic | Document |
|-------|----------|
| Full architecture | ARCHITECTURE.md |
| Intake API | INTAKE_GATEWAY_PLAN |
| Parsing | PARSING_PIPELINE_PLAN |
| MIME allowlist | DOCUMENT_SAFETY |
| Quick start | BUILD_1HR |
