# Frostbyte ETL Planning Pack — Single Source of Truth

**Last updated:** 2026-02-13  
**Deadline:** 2026-02-13 (today)

---

## Mandate

**This document is the sole reference for the project.** Any document or artifact not explicitly listed in the Canonical Document Index below is deemed non-existent and must be disregarded. No document may be introduced into the repository without permission. Diagrams must be high-end only (Mermaid in `diagrams/*.mmd` or fenced Mermaid in docs); raggedy or unprofessional ASCII diagrams are not permitted.

---

## Progress at a Glance

| Metric | Value |
|--------|--------|
| **Planning** | 17/18 plans (08-03 role plays not complete) |
| **Phase 1–7** | Complete; Phase 8: 2/3 (role plays outstanding) |
| **Implementation** | Foundation ✅ Storage ✅ Intake ✅ Parsing ✅ Policy/Embed/Serve in progress |
| **Next** | Policy engine → embedding → serving per implementation order |
| **Not complete** | 08-03 role plays (~10 pp each); Docker/offline bundle (only local-dev files exist) |

---

## Roadmap (All Planned Activities)

### Phase 1: Product Definition and Tech Decisions

- [x] **01-01** — Zero-shot PRD (executive summary, pipeline phases, tenant lifecycle, monitoring, API contracts) → `docs/product/PRD.md`
- [x] **01-02** — Technology decisions and version-pinned dependency manifests → `docs/reference/TECH_DECISIONS.md`
- **Status:** Complete (2026-02-08)

### Phase 2: Tenant Isolation Architecture

- [x] **02-01** — Hetzner provisioning and network boundaries → `docs/architecture/TENANT_ISOLATION_HETZNER.md`
- [x] **02-02** — Per-tenant storage namespace and encryption key management → `docs/architecture/TENANT_ISOLATION_STORAGE_ENCRYPTION.md`
- **Status:** Complete (2026-02-09)

### Phase 3: Audit Stream and Document Safety

- [x] **03-01** — Audit event schema, immutable storage, query patterns → `docs/architecture/AUDIT_ARCHITECTURE.md`
- [x] **03-02** — Injection defense, content boundary enforcement, file-type allowlisting → `docs/security/DOCUMENT_SAFETY.md`
- **Status:** Complete (2026-02-11)

### Phase 4: Foundation and Storage Layer Plans

- [x] **04-01** — Foundation layer (tenant data model, config framework, Docker skeleton, audit emission) → `docs/architecture/FOUNDATION_LAYER_PLAN.md`
- [x] **04-02** — Storage layer (MinIO, PostgreSQL, Qdrant, Redis per-tenant provisioning) → `docs/architecture/STORAGE_LAYER_PLAN.md`
- **Status:** Complete (2026-02-11)

### Phase 5: Intake and Parsing Pipeline Plans

- [x] **05-01** — Intake gateway (auth, manifest, checksum, malware, receipts) → `docs/design/INTAKE_GATEWAY_PLAN.md`
- [x] **05-02** — Parsing pipeline (Docling + Unstructured, canonical JSON schema) → `docs/design/PARSING_PIPELINE_PLAN.md`
- **Status:** Complete (2026-02-11)

### Phase 6: Policy, Embedding, and Serving Layer Plans

- [x] **06-01** — Policy engine (PII, classification, injection defense) → `docs/design/POLICY_ENGINE_PLAN.md`
- [x] **06-02** — Embedding and indexing (OpenRouter/Nomic, 768d, three-store write) → `docs/design/EMBEDDING_INDEXING_PLAN.md`
- [x] **06-03** — Serving layer / RAG API (retrieval proof, cite-only-from-retrieval) → `docs/design/SERVING_LAYER_PLAN.md`
- **Status:** Complete (2026-02-11)

### Phase 7: Deployment Architecture

- [x] **07-01** — Online deployment and offline Docker bundle → `docs/architecture/DEPLOYMENT_ARCHITECTURE.md`
- [x] **07-02** — Mode parity matrix and offline update cycle → `docs/reference/MODE_PARITY_AND_OFFLINE_UPDATE.md`
- **Status:** Complete (2026-02-11)

### Phase 8: Team Readiness Documentation

- [x] **08-01** — Engineer onboarding (architecture, dev setup, first-task guide) → `docs/team/ENGINEER_ONBOARDING.md`
- [x] **08-02** — Vendor operations guide (Dana persona) → `docs/operations/VENDOR_OPERATIONS_GUIDE.md`
- [ ] **08-03** — Role-playing scenarios (CS and deployed engineer) → `docs/team/ROLE_PLAYING_SCENARIOS.md` — **Not complete** (content present but not done/validated per user)
- **Status:** 2/3 complete. 08-03 role plays not done.

---

## Phase Progress Summary

| Phase | Plans | Completed | Status |
|-------|-------|-----------|--------|
| 1. Product Definition and Tech Decisions | 2/2 | 2026-02-08 | Complete |
| 2. Tenant Isolation Architecture | 2/2 | 2026-02-09 | Complete |
| 3. Audit Stream and Document Safety | 2/2 | 2026-02-11 | Complete |
| 4. Foundation and Storage Layer | 2/2 | 2026-02-11 | Complete |
| 5. Intake and Parsing Pipeline | 2/2 | 2026-02-11 | Complete |
| 6. Policy, Embedding, and Serving | 3/3 | 2026-02-11 | Complete |
| 7. Deployment Architecture | 2/2 | 2026-02-11 | Complete |
| 8. Team Readiness | 2/3 | — | 08-03 role plays not complete |

**Total:** 17/18 plans delivered. 08-03 (role-playing scenarios) not complete.

---

## Implementation Status (What Is Built vs Planned)

| Layer | Status | Notes |
|-------|--------|--------|
| Foundation | Done | Migrations 001, 002; PlatformConfig; load_tenant_config; emit_audit_event; create_tenant |
| Storage | Done | MinIO, PostgreSQL, Qdrant, Redis provisioners; provision_tenant_storage; credentials + SOPS |
| Intake | Done | Batch manifest, MIME/checksum/size; POST batch, GET batch, GET receipt; audit events; MinIO raw |
| Parsing | Done | pipeline/parsing/; Unstructured + chunk_by_title; canonical JSON; parse worker; idempotency |
| Policy | Planned | Per docs/design/POLICY_ENGINE_PLAN.md |
| Embedding | Planned | Per docs/design/EMBEDDING_INDEXING_PLAN.md |
| Serving | Planned | Per docs/design/SERVING_LAYER_PLAN.md |
| Deployment | Docs only | Runbooks and bundle spec in docs/architecture/DEPLOYMENT_ARCHITECTURE.md |

**Implementation order:** Foundation → Storage → Intake → Parsing → Policy → Embedding → Serving (per HANDOFF.md and BUILD_1HR.md).

---

## Canonical Document Index

**Only these documents exist.**
 All paths are relative to repository root.

### Planning (this document and supporting state)

- `.planning/PROJECT.md` — **This file. Single source of truth.**
- `.planning/STATE.md` — Project state snapshot (reference only; PROJECT.md is authority)
- `.planning/ROADMAP.md` — Roadmap detail (reference only; PROJECT.md is authority)
- `.planning/REQUIREMENTS.md` — Requirement IDs (PRD-*, TECH-*, IMPL-*, etc.)

### Product and reference

- `docs/product/PRD.md` — Product requirements, pipeline lifecycle, tenant lifecycle, API contracts, metrics
- `docs/reference/TECH_DECISIONS.md` — Component technology choices (version-pinned)
- `docs/reference/MODE_PARITY_AND_OFFLINE_UPDATE.md` — Mode parity matrix, offline update cycle

### Architecture

- `docs/architecture/FOUNDATION_LAYER_PLAN.md` — Tenant data model, config framework, Docker skeleton, audit emission
- `docs/architecture/STORAGE_LAYER_PLAN.md` — MinIO, PostgreSQL, Qdrant, Redis provisioning
- `docs/architecture/TENANT_ISOLATION_HETZNER.md` — Hetzner provisioning, network boundaries
- `docs/architecture/TENANT_ISOLATION_STORAGE_ENCRYPTION.md` — Storage namespaces, encryption, key rotation
- `docs/architecture/AUDIT_ARCHITECTURE.md` — Audit schema, immutable storage, query patterns
- `docs/architecture/DEPLOYMENT_ARCHITECTURE.md` — Online topology, offline Docker bundle, runbooks

### Design (implementation plans)

- `docs/design/INTAKE_GATEWAY_PLAN.md` — Intake flow, API endpoints, audit events
- `docs/design/PARSING_PIPELINE_PLAN.md` — Docling + Unstructured, canonical schema, lineage
- `docs/design/POLICY_ENGINE_PLAN.md` — PII, classification, injection defense
- `docs/design/EMBEDDING_INDEXING_PLAN.md` — OpenRouter/Nomic, 768d, three-store write
- `docs/design/SERVING_LAYER_PLAN.md` — RAG retrieval, retrieval proof, cite-only-from-retrieval
- `docs/design/PIPELINE_FLOW.md` — High-level pipeline flow (references diagrams)
- `docs/design/WORKERS.md` — Worker scripts and queues

### Security

- `docs/security/DOCUMENT_SAFETY.md` — Injection defense, content boundary, file allowlisting

### Operations

- `docs/operations/VENDOR_OPERATIONS_GUIDE.md` — Batch submission, acceptance reports, troubleshooting (Dana)
- `docs/operations/DOCKER_TROUBLESHOOTING.md` — Docker issues and remediation
- `docs/operations/DEPLOY_FOR_FROSTY.md` — Deploy app + onboarding (Vercel + backend); no Gradio; what must be available

### Team

- `docs/team/ENGINEER_ONBOARDING.md` — Architecture walkthrough, dev setup, first-task guide
- `docs/team/ROLE_PLAYING_SCENARIOS.md` — CS and deployed engineer scenarios **(not complete; target ~10 pages per scenario)**
- `docs/team/BRIEF_INTRO_ENTERPRISE_DATA_PIPELINES.md` — Brief intro (onboarding)

### Diagrams (high-end only; Mermaid)

- `diagrams/architecture.mmd` — Pipeline architecture (flowchart)
- `diagrams/tenancy.mmd` — Control plane and tenant isolation (flowchart)
- `diagrams/offline_bundle.mmd` — Offline bundle layout (flowchart)

### Root-level operational

- `HANDOFF.md` — Agent handoff; session continuity (reference only)
- `BUILD_1HR.md` — Quick start and 1-hour build steps

### Docker (not complete)

- **Docker / offline bundle:** **Not complete.** Only local-dev artifacts exist. Full offline Docker bundle per Phase 7 (DEPLOYMENT_ARCHITECTURE) is not delivered.
- `Dockerfile` — Repo root. Exists for local/dev only (Pipeline API image; Python 3.12, tesseract, ffmpeg). Build: `docker build -t frostbyte-pipeline .`
- `docker-compose.yml` — Repo root. Local stack only (MinIO, Postgres, Redis, Qdrant). No pipeline service in compose; run API separately. **Not the production/offline bundle.**
- `docker-compose.test.yml` — Repo root. Test stack for compliance tests.

---

## Key Decisions (Condensed)

- **PRD and TECH_DECISIONS** are the product and technology authority (Phase 1).
- **Embedding dimension:** 768d (both online and offline); Nomic v1.5 for offline.
- **MinIO:** Retained despite maintenance mode (Option A).
- **Qdrant:** Collection per tenant (`tenant_{id}`).
- **Isolation:** Per-tenant namespaces everywhere; credentials and SOPS per tenant.
- **Audit:** Append-only `audit_events`; hash chain for document provenance.
- **Diagrams:** Only Mermaid (in `diagrams/*.mmd` or fenced in docs). No raggedy ASCII.

---

## How Progress Is Tracked

- **Planning:** Checkboxes in Roadmap section above; Phase Progress Summary table.
- **Implementation:** Implementation Status table (Done vs Planned).
- **Documents:** Canonical Document Index is the only list of existing docs.
- **Handoff:** HANDOFF.md is updated at session end for continuity; PROJECT.md remains the single source of truth.
- **End-to-end document test:** The only E2E document test that counts is the one the designated tester (e.g. Mr. Frostbyte) runs himself. Automated scripts are for convenience only; they do not replace that test.

---

## Verification and Truth (V&T)

- **Exists:** This document (`.planning/PROJECT.md`) as the single source of truth; 17/18 plans delivered; canonical document index and diagram paths as stated. **Not complete:** 08-03 role plays (target ~10 pages each). **Docker/offline bundle:** Not complete — only local-dev `Dockerfile` and `docker-compose*.yml` at repo root; full offline bundle per 07-01 not delivered.
- **Does not exist:** Any document or diagram not listed in the Canonical Document Index; unapproved artifacts; raggedy ASCII diagrams (they are out).
- **Unverified:** Implementation completeness of policy, embedding, and serving layers (planned, not verified in this document); role-play scenarios (08-03) not done per user.
- **Functional status:** Phase 8: 2/3 (role plays outstanding). Foundation, storage, intake, and parsing implemented per HANDOFF.md; policy/embedding/serving next in order.
