# Agent Handoff: Frostbyte ETL Planning Pack

**Single source of truth:** `.planning/PROJECT.md` — roadmap, progress, canonical document index. This file is for session continuity only; PROJECT.md is authority.

**Date:** 2026-02-17
**Status:** Pipeline Standing — 1hr Build + 3 Enhancements

## What Was Just Completed

- **Pipeline startup investigation and script fixes** — Root cause: `./scripts/pipeline-manager.sh auto` fails when Docker Compose infra (PostgreSQL:5433, MinIO:9000, Qdrant:6333) is not running. Redis was OK (local or single service). Changes in `scripts/pipeline-manager.sh`: (1) `POSTGRES_URL` for local API start corrected from port 5432 to 5433 to match `docker-compose.yml` host mapping; (2) on infrastructure failure, script now prints project root path and checks Docker daemon — if Docker is not running, suggests starting Docker Desktop first, then `cd $PROJECT_ROOT && docker-compose up -d`. **User fix:** Start Docker, then from repo root run: `docker-compose up -d` (or `docker-compose up -d postgres minio qdrant` if Redis is already up).
- **Zero-shot Admin Dashboard (Monochrome Machine + PRD)** — Full implementation at `packages/admin-dashboard`: Pipeline Schematic (ASCII DAG, [INTAKE]→[PARSE]→…→[VERIFY]); Tenant Chambers grid; Document Queue (ID, NAME, SIZE, STATUS, VERIFICATION, [↑][↓] reorder, [VERIFY][INSPECT]); Verification Control Room (Gate 1 Evidence, Gate 2 Retrieval, Gate 3 Red-Team); Pipeline Control Panel ([ONLINE][OFFLINE][HYBRID], model radio, batch size, [COMMIT]); Audit Gallery (timestamp, tenant, operation, fingerprint, [VERIFY][EXP]); Inspector modal (chain of custody); top-bar nav [DASH][TENANTS][DOCS][VERIFY][CONTROL][AUDIT]; Zustand+Immer store; metal palette, IBM Plex Mono, zero radius, no shadows. Run: `cd packages/admin-dashboard && npm run dev` → http://localhost:5174/admin.
- **Enhancement #6 — Admin Dashboard** — React + TypeScript + Vite dashboard at `packages/admin-dashboard`: Dashboard (health), Tenants (list/detail + schema), Documents (lookup by ID), Jobs, Settings, Login (mocked). Run: `cd packages/admin-dashboard && npm run dev`, then http://localhost:5174/admin.
- **Enhancement #9 — Multi-Modal Document Support** — Implemented full multimodal pipeline: modality detection (`pipeline/multimodal/detector.py`), image processor (OCR + CLIP), audio (Whisper), video (ffmpeg + frames + OCR + CLIP); migration `007_add_multimodal_support.sql` (documents, chunks, image_embeddings, video_frames with pgvector); `embedding.py`, `vector_store.py`; `scripts/run_multimodal_worker.py` consumes Redis `multimodal:jobs`; intake extended (POST /api/v1/intake dispatches image/audio/video to worker); POST /api/v1/collections/{name}/query accepts `query_file` for image/audio/video; `.env.example` multimodal vars; `Dockerfile` with tesseract-ocr, ffmpeg. Run worker: `python scripts/run_multimodal_worker.py` (from project root, pipeline installed). **Note:** Migration 007 requires pgvector extension in PostgreSQL; use `ankane/pgvector` or equivalent.
- **All‑In‑One Zero‑Shot PRDs for Enhancements 5, 7, 8** — `specs/E05-GRAPH-RAG-PRD.md`, `specs/E07-SSO-SAML-OIDC-PRD.md`, `specs/E08-SIGNED-EXPORT-BUNDLES-PRD.md` created. Each contains COSTAR system prompt, Zero‑Shot prompt, PRD, and deterministic implementation plan. E05: Graph RAG — Neo4j, spaCy entity extraction, hybrid vector+graph query endpoint, background graph ingest. E07: SSO/OIDC — Auth0 integration, login/callback flow, session cookie, protected routes. E08: Signed export bundles — GPG signing, tar.gz + manifest.json, Redis export worker, `frostbyte-verify` CLI.
- **All‑In‑One Zero‑Shot PRDs for Enhancements 2, 3, 6** — `specs/E02-TERRAFORM-PROVIDER-PRD.md`, `specs/E03-BATCH-API-PRD.md`, `specs/E06-ADMIN-DASHBOARD-PRD.md` created. Each contains COSTAR system prompt, Zero‑Shot prompt, PRD, and deterministic implementation plan. E02: Terraform provider (frostbyte_tenant resource + data source). E03: Batch API with SSE streaming, Redis queue, `pipeline/pipeline/routes/batch.py` and `worker/batch_worker.py`. E06: React+TypeScript+Vite admin dashboard with tenants, documents, jobs, settings.
- **Enhancement #1 — OpenAPI/Swagger Spec** — `specs/openapi.yaml` created with all six mandatory endpoints (POST /documents, GET /documents/{id}, GET /documents/{id}/chunks, POST /collections, POST /collections/{name}/query, GET /health). Validates with `npx @apidevtools/swagger-cli validate specs/openapi.yaml`.
- **Enhancement #4 — Configurable Schema Extensions** — Migration `006_tenant_schemas.sql` creates `tenant_schemas` table; `pipeline/pipeline/schemas/tenant_schema.py` (Pydantic models); `pipeline/pipeline/routes/tenant_schemas.py` (PUT/GET/PATCH `/tenants/{tenant_id}/schema`); `schema_validation.py` for JSON Schema validation. Added `jsonschema` dep. Run migration: `./scripts/run_migrations.sh` (includes 006).
- **Enhancement #10 — Automated Compliance Test Suite** — `pipeline/tests/compliance/`: GDPR, HIPAA, FedRAMP templates; `conftest.py` (client, db fixtures); `test_tenant_schema.py` for schema endpoints; `docker-compose.test.yml`. Run: `python -m pytest pipeline/tests/compliance -v`. Many tests skip until endpoints (DELETE documents, export, metrics, API keys) exist.
- **Pipeline stood up per BUILD_1HR.md** — Docker Compose (MinIO, PostgreSQL:5433, Redis, Qdrant); migrations 001, 002, 005 via `./scripts/run_migrations.sh`; pipeline installed (`pip install -e .`); API running at http://localhost:8000; intake tested (POST /api/v1/intake); document metadata, Qdrant `tenant_default` collection, MinIO bucket verified.
- **Port 5433 for Postgres** — `docker-compose.yml` and `scripts/run_migrations.sh` updated to avoid conflict with host Postgres on 5432. API start command in BUILD_1HR includes `FROSTBYTE_CONTROL_DB_URL` with port 5433.
- **Parsing pipeline implementation** — `pipeline/parsing/`: CanonicalStructuredDocument models; Unstructured partition + chunk_by_title; parse_file() → canonical JSON; MinIO write to normalized/{tenant_id}/{doc_id}/structured.json; DOCUMENT_PARSED, DOCUMENT_PARSE_FAILED audit events; policy job enqueue to tenant:{tenant_id}:queue:policy. Worker: `scripts/run_parse_worker.py` BRPOPs from tenant parse queues, downloads from MinIO, parses, writes, audits. Idempotency: skip if canonical exists. Added docling, unstructured[all-docs] deps. Intake enqueue now includes mime_type.
- **Intake gateway (prior)** — JWT auth (bypass FROSTBYTE_AUTH_BYPASS=1), rate limit (100/min), ClamAV, Redis parse enqueue, PostgreSQL receipt persistence.
- **Intake gateway implementation** — `pipeline/intake/`: BatchManifest, IntakeReceipt models; MIME sniffing (python-magic), checksum, size validation; POST /api/v1/ingest/{tenant_id}/batch (202 Accepted), GET batch, GET receipt; BATCH_RECEIVED, DOCUMENT_INGESTED, DOCUMENT_REJECTED, DOCUMENT_QUARANTINED audit events; MinIO write to raw/{tenant_id}/{file_id}/{sha256}.
- **Storage layer implementation** — `pipeline/storage/`: MinIO, PostgreSQL, Qdrant, Redis provisioners; credential generation + SOPS; combined `provision_tenant_storage` with rollback; `get_collection_name`, `verify_tenant_access`. Unit tests in `pipeline/tests/test_storage.py`. Added `redis` dep.
- **E2E verification** — `scripts/verify_e2e.sh` (runs when Docker is healthy); `docs/operations/DOCKER_TROUBLESHOOTING.md` for 500 error remediation.
- **Foundation layer implementation** — migrations 001, 002; PlatformConfig; load_tenant_config; emit_audit_event; decrypt_tenant_secrets; create_tenant with audit emission; migration runner `scripts/run_migrations.sh`; BUILD_1HR Step 0; .env.example FROSTBYTE_* vars
- **Planning consistency** — STATE.md and ROADMAP.md Phase 2 checkboxes updated to reflect 100% completion
- **Phase 8 (Team Readiness Documentation)** — **complete** (3/3 plans)
  - **Plan 08-01** — `docs/team/ENGINEER_ONBOARDING.md`: Architecture walkthrough, dev setup, first-task guide
  - **Plan 08-02** — `docs/operations/VENDOR_OPERATIONS_GUIDE.md`: Batch submission, acceptance reports, troubleshooting (Dana)
  - **Plan 08-03** — `docs/team/ROLE_PLAYING_SCENARIOS.md`: CS scenarios (3), deployed engineer scenarios (3)
  - Phase 8 folder: `.planning/phases/08-team-readiness/` with 08-RESEARCH.md, 08-01/02/03-PLAN.md, summaries
- **All 8 phases complete.** Zero-Shot Implementation Pack v1.0 delivered.

## Previous: Phase 7 (Deployment Architecture) — complete (2/2 plans)
  - **Plan 07-01** — `docs/architecture/DEPLOYMENT_ARCHITECTURE.md`: Online Hetzner topology, runbook, offline Docker bundle (compose, images, models, scripts)
  - **Plan 07-02** — `docs/reference/MODE_PARITY_AND_OFFLINE_UPDATE.md`: Mode parity matrix, six divergences with workarounds, offline update cycle
  - Phase 7 folder: `.planning/phases/07-deployment-architecture/` with 07-RESEARCH.md, 07-01/02-PLAN.md, summaries
- Phase 1–7 all complete

## Previous: Phase 6 (Policy, Embedding, and Serving Layer Plans) — complete (3/3 plans)
  - **Plan 06-01** — `docs/design/POLICY_ENGINE_PLAN.md`: PII (REDACT/FLAG/BLOCK), classification (rule+ML), injection (DOCUMENT_SAFETY)
  - **Plan 06-02** — `docs/design/EMBEDDING_INDEXING_PLAN.md`: OpenRouter/Nomic, 768d, three-store write, rollback
  - **Plan 06-03** — `docs/design/SERVING_LAYER_PLAN.md`: RAG retrieval, retrieval proof, cite-only-from-retrieval
  - Phase 6 folder: `.planning/phases/06-policy-embedding-serving/` with 06-RESEARCH.md, 06-01/02/03-PLAN.md, summaries
- Phase 1–6 all complete

## Previous: Phase 5 (Intake and Parsing Pipeline Plans) — complete (2/2 plans)
  - **Plan 05-01** — `docs/design/INTAKE_GATEWAY_PLAN.md` created:
    - Full request flow: auth, manifest validation, MIME/size/checksum/malware checks
    - API endpoints (POST batch, GET batch, GET receipt), error response formats
    - Audit events: BATCH_RECEIVED, DOCUMENT_INGESTED, DOCUMENT_REJECTED, DOCUMENT_QUARANTINED
  - **Plan 05-02** — `docs/design/PARSING_PIPELINE_PLAN.md` created:
    - Docling + Unstructured orchestration (Stage 1 layout, Stage 2 chunking, Stage 3 assembly)
    - Canonical JSON schema (Pydantic-ready models)
    - Lineage, deterministic chunk_id, parse failure reporting
  - Phase 5 folder: `.planning/phases/05-intake-and-parsing/` with 05-RESEARCH.md, 05-01-PLAN.md, 05-02-PLAN.md, summaries
- Phase 1, Phase 2, Phase 3, Phase 4, and Phase 5 all complete

## Previous: Phase 4 (Foundation and Storage Layer) — complete (2/2 plans)
  - **Plan 04-01** — `docs/architecture/FOUNDATION_LAYER_PLAN.md` created:
    - Tenant data model (tenants table DDL, migrations/001_tenant_registry.sql)
    - Configuration framework (env vars, tenant config JSONB, SOPS secrets)
    - Docker Compose skeleton (migration order, audit DDL reference)
    - Audit event emission (emit_audit_event, TENANT_CREATED/PROVISION_STARTED/PROVISIONED/CONFIG_UPDATED)
  - **Plan 04-02** — `docs/architecture/STORAGE_LAYER_PLAN.md` created:
    - MinIO, PostgreSQL, Qdrant, Redis per-tenant provisioning
    - Credential generation and SOPS workflow
    - Combined provisioning sequence with rollback
    - Cross-store verification and audit emission
  - Phase 4 folder: `.planning/phases/04-foundation-and-storage-layer/` with 04-RESEARCH.md, 04-01-PLAN.md, 04-02-PLAN.md, summaries
- Phase 1, Phase 2, Phase 3, and Phase 4 all complete

## Previous: Phase 3 (Audit Stream and Document Safety) — complete (2/2 plans)
  - **Plan 03-01** — `docs/architecture/AUDIT_ARCHITECTURE.md` created:
    - Audit event schema (fields, 24+ event types, hash chain design)
    - Immutable storage (PostgreSQL DDL, GRANT/REVOKE, optional trigger)
    - Query patterns (by tenant, by document, by time range) with example SQL and export format (JSON Lines + manifest)
  - **Plan 03-02** — `docs/security/DOCUMENT_SAFETY.md` created:
    - Injection defense (10+ regex patterns, heuristic scorer, PASS/FLAG/QUARANTINE decision tree)
    - Content boundary enforcement (envelope pattern at Stages A–E, delimiter spec)
    - File-type allowlisting (MIME verification via libmagic, per-tenant config)
  - Phase 3 folder: `.planning/phases/03-audit-stream-and-document-safety/` with 03-RESEARCH.md, 03-01-PLAN.md, 03-02-PLAN.md, summaries
- Phase 1, Phase 2, and Phase 3 all complete

## Current Project State

### What's Working

- `docs/product/PRD.md` — full pipeline lifecycle, 4 personas, tenant lifecycle (7 states, 13 transitions), 17 API endpoints, 20 metrics
- `docs/reference/TECH_DECISIONS.md` — 35 component decisions (version-pinned), online/offline manifests, 768d embedding lock
- Phase 2 research — verified patterns for Hetzner provisioning, SOPS+age, MinIO/PostgreSQL/Qdrant isolation, Docker `internal: true`
- `docs/architecture/TENANT_ISOLATION_HETZNER.md` — Hetzner provisioning, firewall rules, Docker offline
- `docs/architecture/TENANT_ISOLATION_STORAGE_ENCRYPTION.md` — storage namespaces, encryption, key rotation
- `docs/architecture/AUDIT_ARCHITECTURE.md` — audit schema, immutable storage, query patterns
- `docs/security/DOCUMENT_SAFETY.md` — injection defense, content boundary, file allowlisting
- `docs/architecture/FOUNDATION_LAYER_PLAN.md` — tenant data model, config framework, Docker skeleton, audit emission
- `docs/architecture/STORAGE_LAYER_PLAN.md` — MinIO, PostgreSQL, Qdrant, Redis provisioning, credentials, verification
- `docs/design/INTAKE_GATEWAY_PLAN.md` — Intake flow, API endpoints, MIME/checksum/malware, receipts
- `docs/design/PARSING_PIPELINE_PLAN.md` — Docling + Unstructured, canonical JSON schema, lineage
- `docs/design/POLICY_ENGINE_PLAN.md` — PII, classification, injection (DOCUMENT_SAFETY)
- `docs/design/EMBEDDING_INDEXING_PLAN.md` — OpenRouter/Nomic, 768d, three-store write
- `docs/design/SERVING_LAYER_PLAN.md` — RAG retrieval, retrieval proof, cite-only-from-retrieval
- `docs/architecture/DEPLOYMENT_ARCHITECTURE.md` — Online Hetzner topology, provisioning runbook, offline bundle
- `docs/reference/MODE_PARITY_AND_OFFLINE_UPDATE.md` — Mode parity matrix, offline update cycle
- `docs/team/ENGINEER_ONBOARDING.md` — Architecture, dev setup, first-task guide
- `docs/operations/VENDOR_OPERATIONS_GUIDE.md` — Dana: batch submission, acceptance reports, troubleshooting
- `docs/team/ROLE_PLAYING_SCENARIOS.md` — CS and deployed engineer role-play scenarios

### Project Structure

```
.planning/             # Planning state, phases, research
  phases/
    01-.../            # Phase 1 — complete (01-VERIFICATION.md passed)
    02-.../            # Phase 2 — complete (02-01, 02-02 summaries; TENANT_ISOLATION_*.md)
    03-audit-stream-and-document-safety/   # Phase 3 — complete (03-01, 03-02; AUDIT_*, DOCUMENT_SAFETY)
    04-foundation-and-storage-layer/       # Phase 4 — complete (04-01, 04-02; FOUNDATION_*, STORAGE_*)
    05-intake-and-parsing/                 # Phase 5 — complete (05-01, 05-02; INTAKE_*, PARSING_*)
    06-policy-embedding-serving/           # Phase 6 — complete (06-01, 06-02, 06-03; POLICY_*, EMBEDDING_*, SERVING_*)
    07-deployment-architecture/           # Phase 7 — complete (07-01, 07-02; DEPLOYMENT_*, MODE_PARITY_*)
    08-team-readiness/                    # Phase 8 — complete (08-01, 08-02, 08-03; ENGINEER_*, VENDOR_*, ROLE_*)
  research/            # ARCHITECTURE, FEATURES, PITFALLS, STACK
docs/                  # PRD, TECH_DECISIONS, NOTION_EXPORT, api/openapi.yaml
packages/api|core/     # API server, schema extension service
schemas/               # tenant-custom-schema.json
migrations/            # 001_tenant_registry, 002_audit_events, 004_add_custom_metadata
notebooks/             # 5 variant notebooks (05 = Hetzner multi-tenant)
```

## Recommended Next Steps

1. **Implement enhancement PRDs** — Execute `specs/E02-TERRAFORM-PROVIDER-PRD.md`, `specs/E03-BATCH-API-PRD.md`, `specs/E06-ADMIN-DASHBOARD-PRD.md`, `specs/E05-GRAPH-RAG-PRD.md`, `specs/E07-SSO-SAML-OIDC-PRD.md`, `specs/E08-SIGNED-EXPORT-BUNDLES-PRD.md` per their deterministic implementation plans.
2. **Policy engine** — Next per implementation order: `docs/design/POLICY_ENGINE_PLAN.md` (PII detection, classification, injection defense; consume from tenant:{tenant_id}:queue:policy)
3. **Build + E2E** — `docker compose up -d`, `./scripts/run_migrations.sh`, `cd pipeline && pip install -e . && uvicorn pipeline.main:app --port 8000`. In another terminal: `python scripts/run_parse_worker.py`. Submit batch via POST /api/v1/ingest/{tenant_id}/batch; worker parses, writes canonical JSON, enqueues policy.
4. **Phase 1 UAT** (optional) — `01-UAT.md` shows 8 tests pending

## Prompt for Next Conversation

No further roadmap phases. For implementation work:

```
Implement [component] per docs/[PLAN].md. Reference HANDOFF.md for project state. Follow implementation plans in order: foundation → storage → intake → parsing → policy → embedding → serving. Deployment per DEPLOYMENT_ARCHITECTURE.md.
```

## Important Context

### Design Principles

- Every artifact must be **deterministic** — engineer or AI can execute without interpretation
- No "choose between X and Y" — one technology, one rationale per component
- Tenant isolation is **by construction**, not policy; per-tenant namespaces everywhere

### Tech Stack (from Phase 1)

- Hetzner Cloud, hcloud SDK >=2.10, MinIO, PostgreSQL >=16, Qdrant >=1.13, Redis >=8
- SOPS >=3.8 + age >=1.2 for envelope encryption
- Docker Compose >=2.29 for offline mode; `internal: true` networks for air-gap isolation

### Key Files to Review

- `docs/product/PRD.md` Section 3.4 (provisioning), 3.6 (deprovisioning)
- `docs/architecture/AUDIT_ARCHITECTURE.md` — audit schema, immutable storage, query patterns
- `docs/security/DOCUMENT_SAFETY.md` — injection defense, content boundary, file allowlisting
- `.planning/phases/02-tenant-isolation-architecture/02-RESEARCH.md` — patterns and pitfalls
- `docs/reference/TECH_DECISIONS.md` — component choices

## Known Issues / Considerations

- **Pipeline auto-start:** `./scripts/pipeline-manager.sh auto` (and `make pipeline-auto`) require Docker to be running and infra up. If you see "PostgreSQL/MinIO/Qdrant not running", start Docker Desktop then run `docker-compose up -d` from the project root. Script now prints project root and suggests starting Docker when the daemon is not running.
- Docker daemon returned 500 Internal Server Error when pulling images — user must fix Docker (see `docs/operations/DOCKER_TROUBLESHOOTING.md`). Run `./scripts/verify_e2e.sh` once Docker is healthy to verify end-to-end.
- `openmemory.md` is empty — no stored project memories yet
- 01-UAT.md has 8 pending tests (manual UAT); 01-VERIFICATION.md shows 13/13 passed (automated verification)
- Phase 2 plan order: 02-01 (Hetzner) then 02-02 (storage/encryption); research supports both

## Quick Reference

- **Project:** Frostbyte ETL Zero-Shot Implementation Pack
- **Branch:** master
- **Last Commit:** (pending) — foundation layer implementation
- **Progress:** 100% (All 8 phases complete)
- **Phase 8 Plans:** 3/3 complete

---

**Status:** Roadmap complete; all 8 phases delivered
**Recommendation:** Begin implementation per docs/ plans; no further planning phases
**Confidence:** High — Zero-Shot Implementation Pack v1.0 complete
