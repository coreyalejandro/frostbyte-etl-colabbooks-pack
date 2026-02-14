# Docs taxonomy

Single place to find and classify pipeline-repo documentation. **Rule:** every doc lives in exactly one category; new docs go in the category below that fits; link from here so paths stay predictable.

---

## Categories and where things live

| Category | Purpose | Path | Contents |
|----------|---------|------|----------|
| **product** | What we're building — PRD, vision, proposals, journey | `docs/product/` | PRD, ETL proposal, customer journey, Notion export |
| **architecture** | System topology — deployment, tenant, audit, foundation, storage | `docs/architecture/` | Deployment, audit, tenant isolation, foundation plan, storage plan |
| **design** | Pipeline/feature design — intake, parse, policy, embed, serve, flow | `docs/design/` | Intake, parsing, policy, embedding, serving plans; pipeline flow; workers |
| **operations** | Runbooks, troubleshooting, vendor ops | `docs/operations/` | Docker troubleshooting, vendor operations guide |
| **security** | Document safety, threat model, encryption | `docs/security/` | Document safety, threat model, tenant isolation encryption |
| **team** | Onboarding and training | `docs/team/` | Brief intro to enterprise pipelines, engineer onboarding, role-playing scenarios |
| **reference** | One-off decisions and background | `docs/reference/` | Tech decisions, mode parity, offline update |
| **api** | API surface | `docs/api/` | OpenAPI spec |
| **notion_variants** | Variant narratives (Notion exports) | `docs/notion_variants/` | Numbered variant docs |

---

## Index (by category)

### product
- [PRD.md](product/PRD.md) — Product requirements, personas, pipeline lifecycle, API, metrics
- [ETL_PIPELINE_PROPOSAL.md](product/ETL_PIPELINE_PROPOSAL.md) — ETL pipeline proposal
- [CUSTOMER_JOURNEY_MAP.md](product/CUSTOMER_JOURNEY_MAP.md) — Customer journey
- [NOTION_EXPORT.md](product/NOTION_EXPORT.md) — Notion export / product context

### architecture
- [DEPLOYMENT_ARCHITECTURE.md](architecture/DEPLOYMENT_ARCHITECTURE.md) — Online Hetzner, offline bundle, runbook
- [AUDIT_ARCHITECTURE.md](architecture/AUDIT_ARCHITECTURE.md) — Audit schema, immutable storage, query patterns
- [TENANT_ISOLATION_HETZNER.md](architecture/TENANT_ISOLATION_HETZNER.md) — Hetzner provisioning, firewall, Docker offline
- [TENANT_ISOLATION_STORAGE_ENCRYPTION.md](architecture/TENANT_ISOLATION_STORAGE_ENCRYPTION.md) — Storage namespaces, encryption, key rotation
- [FOUNDATION_LAYER_PLAN.md](architecture/FOUNDATION_LAYER_PLAN.md) — Tenant data model, config, Docker skeleton, audit
- [STORAGE_LAYER_PLAN.md](architecture/STORAGE_LAYER_PLAN.md) — MinIO, PostgreSQL, Qdrant, Redis provisioning

### design
- [INTAKE_GATEWAY_PLAN.md](design/INTAKE_GATEWAY_PLAN.md) — Intake flow, API, MIME/checksum/malware, receipts
- [PARSING_PIPELINE_PLAN.md](design/PARSING_PIPELINE_PLAN.md) — Docling/Unstructured, canonical JSON, lineage
- [POLICY_ENGINE_PLAN.md](design/POLICY_ENGINE_PLAN.md) — PII, classification, injection (DOCUMENT_SAFETY)
- [EMBEDDING_INDEXING_PLAN.md](design/EMBEDDING_INDEXING_PLAN.md) — OpenRouter/Nomic, 768d, three-store
- [SERVING_LAYER_PLAN.md](design/SERVING_LAYER_PLAN.md) — RAG retrieval, retrieval proof, cite-only
- [PIPELINE_FLOW.md](design/PIPELINE_FLOW.md) — Pipeline flow overview
- [WORKERS.md](design/WORKERS.md) — Worker pattern, queues, how to run workers

### operations
- [DOCKER_TROUBLESHOOTING.md](operations/DOCKER_TROUBLESHOOTING.md) — Docker 500 and remediation
- [VENDOR_OPERATIONS_GUIDE.md](operations/VENDOR_OPERATIONS_GUIDE.md) — Batch submission, acceptance reports, troubleshooting

### security
- [DOCUMENT_SAFETY.md](security/DOCUMENT_SAFETY.md) — Injection defense, content boundary, file allowlisting
- [THREAT_MODEL_SAFETY.md](security/THREAT_MODEL_SAFETY.md) — Threat model and safety

### team
- [BRIEF_INTRO_ENTERPRISE_DATA_PIPELINES.md](team/BRIEF_INTRO_ENTERPRISE_DATA_PIPELINES.md) — Brief intro to enterprise data pipelines (workers, harnesses, components; Frostbyte mapping)
- [ENGINEER_ONBOARDING.md](team/ENGINEER_ONBOARDING.md) — Architecture walkthrough, dev setup, first task
- [ROLE_PLAYING_SCENARIOS.md](team/ROLE_PLAYING_SCENARIOS.md) — CS and deployed-engineer scenarios

### reference
- [TECH_DECISIONS.md](reference/TECH_DECISIONS.md) — Component choices, version pins, online/offline manifests
- [MODE_PARITY_AND_OFFLINE_UPDATE.md](reference/MODE_PARITY_AND_OFFLINE_UPDATE.md) — Mode parity matrix, offline update cycle

### api
- [openapi.yaml](api/openapi.yaml) — OpenAPI spec

### notion_variants
- `01_baseline_dual_mode_sovereign_etl.md` … `05_multi_tenant_isolation_hetzner.md` — Variant narratives

---

## Rules (best practice)

1. **One category per doc** — Put each doc in exactly one folder above; no duplicates.
2. **Link from this index** — New doc → add one line under the right category so it’s discoverable.
3. **Reference by path** — In code/handoff/planning use full path: `docs/design/POLICY_ENGINE_PLAN.md`.
4. **Naming** — Keep existing `UPPER_SNAKE.md` for current docs; new docs prefer `lowercase-with-dashes.md` or same style as the category.
5. **Root `docs/`** — Only this README and category subdirs (and `api/`, `notion_variants/`). No loose `.md` at top level.
