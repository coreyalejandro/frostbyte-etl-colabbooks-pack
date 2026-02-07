# ETL Pipeline Proposal — Data Sovereignty + Safety (Online + Offline)

## 0) Executive Summary
Build a dual-mode ETL pipeline that supports:
- **Online mode**: API-driven ingestion + optional provider embeddings via OpenRouter.
- **Offline mode**: Docker-run pipeline with **local embeddings (Nomic)** and **no outbound calls**.

Core contract:
- **Document in → Structure out → Stored in DB + Vector**
- **Tenant isolation by construction** (per-tenant environments)
- **Full provenance + audit trails** at every step
- **Injection-resistant ingestion** (documents are untrusted inputs)

## 1) Use For / Do Not Use For

### Use for
- Regulated vendor document onboarding (contracts, policies, SOPs, case/matter files)
- RAG-ready corpora where retrieval provenance must be inspectable
- Dashboards/analytics derived from normalized, governed structured outputs
- Multi-tenant deployments where each tenant’s data/keys/compute are isolated

### Do Not Use for
- Returning “legal citations” unless citations are verifiably derived from stored source slices
- Any workflow allowing untrusted docs to influence tool instructions or control prompts
- Cross-tenant aggregation without explicit de-identification + contractual permission
- “Demo-only” pipelines without manifesting, acceptance checks, and audit logs

## 2) Customer Persona + Context
See `docs/CUSTOMER_JOURNEY_MAP.md` for the full journey.

## 3) Pipeline Phases (Major Components)

### Phase A — Intake Gateway (Trust Boundary)
**Inputs**
- Vendor batch drops (SFTP/HTTPS), API pulls, manual uploads (if needed)

**Responsibilities**
- Tenant authentication/authorization
- Manifest + checksum receipts
- File-type allowlists + malware scanning
- Quotas/rate limits

**Outputs**
- Immutable intake receipt: (tenant_id, file_id, sha256, timestamp, source)

### Phase B — Document Normalization (Structure Extraction)
**Primary tooling**
- **Docling**: document conversion + layout-aware structuring
- **Unstructured**: partitioning/chunking primitives + metadata enrichment

**Deliverable**
- A canonical “Structured Document” JSON with:
  - sections, tables, figures
  - reading order + offsets
  - doc lineage pointers (raw → normalized → chunks)

### Phase C — Policy Gates + Enrichment (Safety + Governance)
**Gates**
- PII/PHI detection & redaction policies (configurable)
- Document classification (contract / invoice / SOP / etc.)
- Prompt/document-injection defenses (see `docs/THREAT_MODEL_SAFETY.md`)
- Deterministic chunking + stable chunk IDs

### Phase D — Storage (DB + Object + Vector)
**Write targets**
- Object store: raw + normalized artifacts
- Relational DB: governance metadata, lineage, job statuses, retention rules
- Vector store: embeddings for retrieval (per-chunk + metadata)

**Key requirement**
- Tenant isolation across all stores (namespaces + keys + IAM policies)

### Phase E — Serving (RAG + Analytics + Agent Networks)
**Surfaces**
- Retrieval API (RAG/agents)
- Analytics extracts (warehouse-ready tables)
- Dashboards

**Operational requirement**
- Observability + audit trails for all retrieval and generation events

## 4) Deployment Modes

### 4.1 Online mode (API)
- Orchestrator provisions per-tenant resources
- Embeddings routed via OpenRouter where permitted
- Provider selection must not violate sovereignty contracts

### 4.2 Offline mode (Docker)
- Compose bundle includes parsers + local embeddings + local storage
- Default networking: no outbound routes
- Export artifacts as signed bundles (normalized JSON + index snapshot)

## 5) Tooling Choices + Alternatives

### Parsing / structuring
Primary:
- Unstructured (OSS)
- Docling

Alternatives:
- Apache Tika
- OCRmyPDF + layout models (scan-heavy)

### Embeddings
Primary:
- Online: OpenRouter embeddings endpoint
- Offline: Nomic embed-text

Alternatives:
- bge / e5 family models for local embeddings
- pgvector for moderate scale

### Vector store
Primary pattern:
- Tenant-scoped Qdrant/Weaviate/pgvector (choose based on ops maturity)

### Infrastructure + tenant isolation
Primary:
- Hetzner Cloud API to provision per-tenant isolated environments

Alternatives:
- Dedicated Kubernetes cluster per tenant (strongest blast-radius control)
- Shared cluster with strict namespaces + network policies (lower cost, higher diligence)

## 6) Acceptance Criteria (Rollout-Ready)
- Manifest parity: 0 missing files vs vendor manifest
- Parse visibility: “what extracted / what dropped” report per file
- Deterministic reruns: reprocess only failed docs/segments
- Provenance: every chunk maps to a source slice + offsets + hash
- Audit: ingestion → chunking → embedding model/version → index write → retrieval events

## 7) Deliverables for Vendor Rollout
- Vendor intake checklist + manifest format
- Acceptance report template (`templates/VENDOR_ACCEPTANCE_REPORT.md`)
- Sandbox tenant environment for trial submissions
- Offline Docker bundle + compatibility matrix (hardware/OS/GPU)

