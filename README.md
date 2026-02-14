# Frostbyte ETL Pipeline — Zero-Shot Implementation Pack

Multi-tenant document ETL: **document in → structure out → stored in DB and vector store.** Dual mode (online/offline). Per-tenant isolation. This repo is the planning pack plus runnable pipeline skeleton for local end-to-end document tests.

**Single source of truth:** [`.planning/PROJECT.md`](.planning/PROJECT.md) — roadmap, progress, canonical docs. Consult only that file for what exists and what is complete.

---

## Run an end-to-end document test

**The only end-to-end document test that counts is the one you run yourself.** The repo and docs are set up so the designated tester (e.g. Mr. Frostbyte) can perform that test; automated scripts are for convenience only and do not replace it.

**Goal:** Ingest a document and verify it flows through the pipeline (MinIO + Qdrant). Follow one of the two paths below.

### Option A: Step-by-step (recommended for first run)

1. **Prerequisites:** Docker Desktop running, Python 3.12+, `docker compose` and `curl` available.

2. **Start infrastructure:**
   ```bash
   docker compose up -d
   docker compose ps   # wait until all services show healthy (~30s)
   ```

3. **Run migrations** (Postgres is on port **5433** to avoid conflict with host):
   ```bash
   ./scripts/run_migrations.sh
   ```

4. **Install and start the pipeline API:**
   ```bash
   cd pipeline && pip install -e .
   FROSTBYTE_CONTROL_DB_URL="postgresql://frostbyte:frostbyte@127.0.0.1:5433/frostbyte" \
   FROSTBYTE_AUTH_BYPASS=1 \
   uvicorn pipeline.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Leave this running; in another terminal continue.

5. **Ingest a test document:**
   ```bash
   echo "Test document for Frostbyte ETL." > /tmp/test.txt
   curl -X POST http://localhost:8000/api/v1/intake \
     -F "file=@/tmp/test.txt" \
     -F "tenant_id=default"
   ```
   Expected: `{"document_id":"...", "status":"ingested", ...}`

6. **Verify:** Open **http://localhost:8000** in a browser (dashboard). Use the `document_id` from the response with:
   ```bash
   curl -s http://localhost:8000/api/v1/documents/<document_id>
   ```

Full runbook: [**BUILD_1HR.md**](BUILD_1HR.md).

### Option B: Automated E2E script (convenience only)

From repo root, with Docker Desktop running:

```bash
./scripts/verify_e2e.sh
```

This starts Docker, runs migrations (port 5433), starts the API, posts a test file to `/api/v1/intake`, and checks the response. **This does not replace the manual end-to-end document test** — the one that counts is the one you run yourself.

---

## What’s in this repo

- **`.planning/PROJECT.md`** — Single source of truth (roadmap, progress, canonical document index).
- **`BUILD_1HR.md`** — Full 1-hour build and end-to-end document test runbook.
- **`docs/product/PRD.md`** — Product requirements; **`docs/reference/TECH_DECISIONS.md`** — Technology choices.
- **`docs/architecture/`** — Foundation, storage, tenant isolation, audit, deployment.
- **`docs/design/`** — Intake, parsing, policy, embedding, serving implementation plans.
- **`diagrams/*.mmd`** — Mermaid diagrams (architecture, tenancy, offline bundle).
- **`pipeline/`** — FastAPI app: intake, MinIO, Qdrant, stub parse/embed; runnable locally.
- **`migrations/`** — SQL migrations (tenant registry, audit events, intake receipts, etc.).
- **`scripts/run_migrations.sh`** — Applies migrations (default Postgres port 5433). **`scripts/verify_e2e.sh`** — E2E test.

---

## Docs and diagrams

- **Canonical list of documents:** See [.planning/PROJECT.md — Canonical Document Index](.planning/PROJECT.md). Only documents listed there are considered to exist.
- **Diagrams:** Use the `.mmd` files in `diagrams/` with any Mermaid-compatible viewer (e.g. GitHub, Mermaid Live).

---

## Quick reference

| Item        | Value |
|------------|--------|
| API (local) | http://localhost:8000 |
| API docs    | http://localhost:8000/docs |
| Postgres (Docker) | port **5433** (user `frostbyte`, db `frostbyte`) |
| MinIO       | http://localhost:9000 (9001 console) |
| Qdrant      | http://localhost:6333 |
