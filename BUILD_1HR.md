# Build the Frostbyte ETL Pipeline in 1 Hour

**Purpose:** Get a runnable end-to-end pipeline (intake → parse → store) in ~60 minutes. Single-tenant, local Docker, offline mode. This is the minimal viable skeleton; full production pipeline follows the PRD and implementation plans.

**References:** `docs/PRD.md`, `docs/TECH_DECISIONS.md`

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
| PostgreSQL| 5432  | Relational metadata              |
| Redis     | 6379  | Queue broker / cache             |
| Qdrant    | 6333  | Vector store (768d)              |

**Visual dashboard:** After starting the API, open **http://localhost:8000** in your browser for a status page with a linear flow diagram.

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

See **`REPRODUCE_ZERO_SHOT.md`** for how to re-run the Phase 1 planning process that produced `docs/PRD.md` and `docs/TECH_DECISIONS.md`.

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
