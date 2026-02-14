# Build the Frostbyte ETL Pipeline in 1 Hour

**Purpose:** Get a runnable end-to-end pipeline (intake → parse → store) in ~60 minutes. Single-tenant, local Docker, offline mode. This is the minimal viable skeleton; full production pipeline follows the PRD and implementation plans.

**The only end-to-end document test that counts is the one the designated tester runs himself.** This runbook supports that test; automated scripts do not replace it.

**References:** `docs/product/PRD.md`, `docs/reference/TECH_DECISIONS.md`

---

## Prerequisites (5 min)

```bash
# Required
docker --version    # >= 24
docker compose version
python3 --version   # >= 3.12

# Optional for API docs
curl
```

---

## Step 0: Run Migrations (Foundation Layer)

If you want tenant registry and audit events (per `docs/architecture/FOUNDATION_LAYER_PLAN.md`):

```bash
# After PostgreSQL is running (Step 1)
./scripts/run_migrations.sh
```

Or manually with psql (use port 5433 to match Docker Postgres):
```bash
PGPORT=5433 psql -h 127.0.0.1 -U frostbyte -d frostbyte -f migrations/001_tenant_registry.sql
PGPORT=5433 psql -h 127.0.0.1 -U frostbyte -d frostbyte -f migrations/002_audit_events.sql
```

---

## Step 1: Start Infrastructure (5 min)

```bash
cd /path/to/frostbyte_etl_colabbooks_pack_2026-02-07

# Start MinIO, PostgreSQL, Redis, Qdrant
docker compose up -d

# Verify all healthy
docker compose ps
# All services should show "healthy" after ~30s
```

| Service   | Port  | Purpose                          |
|-----------|-------|----------------------------------|
| MinIO     | 9000  | Object store (S3-compatible)    |
| PostgreSQL| 5433  | Relational metadata (5433 to avoid host Postgres on 5432) |
| Redis     | 6379  | Queue broker / cache             |
| Qdrant    | 6333  | Vector store (768d)              |

**Visual dashboard:** After starting the API, open **http://localhost:8000** in your browser for a status page with a linear flow diagram.

**Admin dashboard (React):** Run the admin UI for tenant management, documents, and health:

```bash
cd packages/admin-dashboard && npm install && npm run dev
```

Then open **http://localhost:5174/admin**. Sign in with your admin API key (set `FROSTBYTE_ADMIN_API_KEY` on the pipeline server, e.g. `openssl rand -hex 32`).

---

## Step 2: Create Bucket (optional)

The pipeline creates the MinIO bucket automatically on first request. Qdrant collection is also auto-created. Skip this step unless you want to pre-create.

```bash
# Optional: pre-create bucket via mc
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/frostbyte-docs --ignore-existing
```

---

## Step 3: Install Python Pipeline (5 min)

```bash
cd pipeline
pip install -e .
```

`pipeline/pyproject.toml` is minimal — FastAPI, boto3, asyncpg, qdrant-client, pydantic.

---

## Step 4: Start the Pipeline API (1 min)

```bash
cd pipeline
pip install -e .
# Use port 5433 to match Docker Postgres (avoids host Postgres on 5432)
FROSTBYTE_CONTROL_DB_URL="postgresql://frostbyte:frostbyte@127.0.0.1:5433/frostbyte" \
FROSTBYTE_AUTH_BYPASS=1 \
uvicorn pipeline.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Step 5: Ingest a Document (2 min)

```bash
# Create a test PDF or TXT
echo "Test document content for ETL pipeline." > /tmp/test.txt

# POST to intake
curl -X POST http://localhost:8000/api/v1/intake \
  -F "file=@/tmp/test.txt" \
  -F "tenant_id=default"
```

Expected response: `{"document_id": "...", "status": "ingested", ...}`

---

## Step 6: Verify Data Flow

```bash
# Check MinIO: object stored (use mc if installed)
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local/frostbyte-docs/

# Check Qdrant: collections and vectors
curl -s http://localhost:6333/collections | jq .

# Check API: list documents (metadata is in-memory for 1hr MVP)
curl -s http://localhost:8000/api/v1/documents/<document_id>
```

---

## Pipeline Flow (1hr MVP)

```
POST /intake (file + tenant_id)
  → validate
  → store raw file in MinIO
  → parse (stub: extract text)
  → embed (stub: 768d zeros or skip)
  → store metadata (in-memory for 1hr MVP)
  → store vectors in Qdrant (if embed)
  → return receipt
```

**Stubs for 1hr:** Parse = plain text extraction. Embed = 768-dimensional zero vector. No Celery (sync flow). No ClamAV. No JWT (local dev).

---

## Reproduce Zero-Shot PRD Planning

See **`REPRODUCE_ZERO_SHOT.md`** for how to re-run the Phase 1 planning process that produced `docs/product/PRD.md` and `docs/reference/TECH_DECISIONS.md`.

---

## What Comes Next (Post-1hr)

| Phase   | Deliverable                           |
|---------|---------------------------------------|
| Phase 2 | Tenant isolation specs (Hetzner, storage) |
| Phase 3 | Audit schema, injection defense       |
| Phase 4 | Foundation + storage impl plans      |
| Phase 5 | Intake + parsing impl plans          |
| Phase 6 | Policy, embedding, serving impl plans|
| Phase 7 | Deployment architecture              |
| Phase 8 | Onboarding, user docs, scenarios     |

Replace stubs with real Docling + Unstructured parsing, OpenRouter/Nomic embedding, Celery workers, JWT auth, and per-tenant provisioning per the full plans.
