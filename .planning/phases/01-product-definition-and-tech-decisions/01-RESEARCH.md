# Phase 1: Product Definition and Tech Decisions - Research

**Researched:** 2026-02-08
**Domain:** PRD authoring for multi-tenant document ETL pipelines + technology decision finalization
**Confidence:** HIGH (existing research provides strong foundation; version pins verified via WebSearch against PyPI/GitHub releases)

## Summary

Phase 1 produces two planning documents -- a comprehensive PRD and a locked-in technology decisions manifest. This is a document-authoring phase, not a code-writing phase. The research question is: "What do I need to know to write these documents well?"

The project already has extensive research in `.planning/research/` covering STACK, FEATURES, ARCHITECTURE, and PITFALLS. This phase research focuses on (1) verifying and updating the version pins from STACK.md against current releases, (2) identifying the document structure patterns that satisfy the phase's success criteria, (3) resolving open questions from prior research that block document finalization, and (4) cataloguing what existing artifacts already contain vs. what must be written fresh.

**Primary recommendation:** Structure Plan 01-01 (PRD) around the five success criteria as mandatory sections, and Plan 01-02 (Tech Decisions) around resolving every "choose between X and Y" to exactly one choice. Use existing artifacts (ETL_PIPELINE_PROPOSAL.md, CUSTOMER_JOURNEY_MAP.md, THREAT_MODEL_SAFETY.md, ARCHITECTURE.md, FEATURES.md) as source material -- synthesize, do not duplicate.

## Standard Stack

This phase produces documents, not code. The "stack" here is the set of authoring patterns, reference materials, and verified technology data that the documents must contain.

### Core: Verified Technology Versions

All versions below were verified via WebSearch on 2026-02-08 against PyPI, GitHub Releases, or official docs. Changes from the STACK.md estimates are flagged.

| Component | STACK.md Version | Verified Current Version | Status | Source |
| --------- | ---------------- | ----------------------- | ------ | ------ |
| **FastAPI** | >=0.115 | Latest release 2026-02-07 (version number not retrieved but actively releasing) | UPDATE: pin to >=0.115, verify exact latest on PyPI | [GitHub Releases](https://github.com/fastapi/fastapi/releases), [PyPI](https://pypi.org/project/fastapi/) |
| **Pydantic** | >=2.9 | 2.12.5 | UPDATE: raise floor to >=2.10 for Python 3.14 support | [PyPI](https://pypi.org/project/pydantic/) |
| **SQLAlchemy** | >=2.0 | 2.0.46 (stable), 2.1.0b1 (beta) | CONFIRMED: >=2.0.46; note asyncio greenlet no longer auto-installed, use `sqlalchemy[asyncio]` | [GitHub Releases](https://github.com/sqlalchemy/sqlalchemy/releases) |
| **Celery** | >=5.4 | 5.6.2 | UPDATE: raise floor to >=5.6 for memory leak fixes and Python 3.13 support | [PyPI](https://pypi.org/project/celery/) |
| **Redis (server)** | >=7.4 | 8.4 (GA) | UPDATE: raise floor to >=8.0 | [GitHub Releases](https://github.com/redis/redis/releases) |
| **Qdrant (server)** | >=1.12 | 1.16 (with tiered multitenancy) | UPDATE: raise floor to >=1.13; note 1.16 tiered multitenancy feature is directly relevant | [Qdrant Blog](https://qdrant.tech/blog/qdrant-1.16.x/), [GitHub Releases](https://github.com/qdrant/qdrant/releases) |
| **MinIO** | latest | MAINTENANCE MODE (Dec 2025) | CRITICAL CHANGE: MinIO community edition entered maintenance mode. See "Open Questions" section | [InfoQ](https://www.infoq.com/news/2025/12/minio-s3-api-alternatives/) |
| **Docling** | not pinned | 2.72.0 (2026-02-03), requires Python >=3.10 | CONFIRMED: actively maintained, frequent releases | [PyPI](https://pypi.org/project/docling/) |
| **Unstructured** | not pinned | Latest release 2026-01-27, requires Python >=3.10.0 | CONFIRMED: actively maintained | [PyPI](https://pypi.org/project/unstructured/) |
| **Nomic embed-text** | v1 | v2 (MoE, 768d default, Matryoshka to 256d); v1.5 still available (768d, Matryoshka to 64d) | UPDATE: v2 exists but local inference support via Ollama "coming soon"; v1.5 is the safe offline choice | [Hugging Face](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe), [Nomic Blog](https://www.nomic.ai/blog/posts/nomic-embed-text-v2) |
| **Prometheus** | >=2.54 | 3.9.1 (current), 3.5.1 (LTS) | UPDATE: Prometheus 3.x is current; raise floor to >=3.5 | [GitHub Releases](https://github.com/prometheus/prometheus/releases) |
| **structlog** | >=24.4 | 25.5.0 | UPDATE: raise floor to >=25.1 | [PyPI](https://pypi.org/project/structlog/) |
| **hcloud** | >=2.2 | 2.16.0 | UPDATE: raise floor to >=2.10 | [PyPI](https://pypi.org/project/hcloud/) |
| **PostgreSQL** | >=16 | 16 (stable), 17 available | CONFIRMED: >=16 is correct | [PostgreSQL](https://www.postgresql.org/docs/release/) |

### Supporting: OpenRouter Embedding Models

OpenRouter provides an OpenAI-compatible embeddings API supporting multiple models:

| Model | Dimensions | Use Case |
| ----- | ---------- | -------- |
| `openai/text-embedding-3-small` | 1536 (configurable) | Cost-effective online embedding |
| `openai/text-embedding-3-large` | 3072 (configurable) | Higher quality online embedding |
| `qwen/qwen3-embedding-0.6b` | 1024 | Small, fast |
| `qwen/qwen3-embedding-8b` | 4096 | High quality |

**Confidence: MEDIUM** -- OpenRouter model availability changes frequently. The PRD must specify which model(s) to use and pin the dimension count.

**Critical dimension alignment issue:** Nomic embed-text v1.5 produces 768d vectors. OpenRouter models produce different dimensions (1536, 3072, etc.). The PRD must either:

1. Lock both modes to the same dimension (e.g., use OpenRouter's dimension reduction to 768d to match Nomic), OR
2. Document that online and offline vector indices are incompatible and vectors cannot be transferred between modes

This is a product decision that must be resolved in the PRD, not deferred.

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Recommendation |
| ---------- | --------- | -------- | --------------- |
| MinIO (maintenance mode) | Garage (Rust, v2.0, Apache 2.0) | Garage is newer, less battle-tested, but actively developed | **Evaluate Garage** -- MinIO maintenance mode is a real risk for a new project. See Open Questions. |
| MinIO (maintenance mode) | SeaweedFS (Go, Apache 2.0) | More mature than Garage, distributed by default | Alternative if Garage does not meet requirements |
| MinIO (maintenance mode) | Hetzner Object Storage (S3-compat) | Managed service, no self-hosting needed for online mode; but unavailable for offline | Online-only option; still need something for offline bundle |
| Nomic v1.5 (offline) | Nomic v2 MoE (offline) | v2 has better multilingual support and quality but Ollama support "coming soon", not confirmed for local inference yet | **Wait for v2 confirmation before locking in** -- v1.5 is the safe choice for now |

## Architecture Patterns

### Pattern 1: PRD Structure for Zero-Shot Implementation

**What:** A PRD structured so that downstream plan authors (human or AI agent) can write implementation plans without asking clarifying questions. Each section maps directly to a requirement ID.

**When to use:** Phase 1, Plan 01-01.

**Structure:**

```text
PRD Document
|
+-- 1. Executive Summary (PRD-01)
|     - What: one-paragraph product description
|     - Why: business justification
|     - Who: personas (Dana, Frode, Engineers, Auditors)
|     - How: architectural overview (control plane / data plane / audit plane)
|
+-- 2. Pipeline Phase Specifications (PRD-02)
|     - For each phase (intake, parsing, enrichment, storage, serving):
|       - Inputs (data types, sources)
|       - Transformations (what happens to the data)
|       - Outputs (artifacts produced)
|       - Data flow diagram (Mermaid)
|       - Error handling (what happens on failure)
|       - Audit events emitted
|
+-- 3. Tenant Lifecycle Management (PRD-03)
|     - State machine: PENDING -> PROVISIONING -> ACTIVE -> SUSPENDED -> DEPROVISIONING -> DEPROVISIONED
|     - Kill-switch: ACTIVE -> SUSPENDED (instant, reversible)
|     - For each state transition:
|       - Trigger (API call, automatic, manual)
|       - Actions performed
|       - Rollback/undo capability
|       - Audit events emitted
|
+-- 4. Monitoring and Observability (PRD-04)
|     - Job tracking requirements
|     - Alerting requirements (channels, severity, content rules)
|     - Metrics requirements (per-tenant dashboards, resource utilization)
|     - Log requirements (structured, tenant-scoped, no content leakage)
|
+-- 5. API Contract Specification (PRD-05)
|     - Intake API (upload, manifest, status)
|     - Query API (RAG retrieval, search)
|     - Admin API (tenant management, configuration)
|     - Audit API (query, export)
|     - For each endpoint group:
|       - HTTP method + path
|       - Request schema (Pydantic model)
|       - Response schema (Pydantic model)
|       - Auth requirements
|       - Rate limits
|       - Error responses
```

**Why this structure:** Success criterion #1 states "an engineer reading only the PRD can describe the full pipeline lifecycle." This requires the PRD to be self-contained -- no forward references to unwritten documents. Success criterion #3 requires the tenant lifecycle to be detailed enough to implement as a state machine. This means explicit states, transitions, and actions, not prose descriptions.

### Pattern 2: Technology Decision Document

**What:** A document that resolves every component to exactly one technology choice with a rationale. No "choose between" language.

**When to use:** Phase 1, Plan 01-02.

**Structure:**

```text
Tech Decisions Document
|
+-- 1. Component Decision Table
|     - For each component:
|       - Component name
|       - Selected technology (ONE choice)
|       - Version pin (exact or floor)
|       - Rationale (2-3 sentences)
|       - Alternatives considered (table: what, tradeoff, why not)
|
+-- 2. Online Mode Dependency Manifest (TECH-02)
|     - Python packages (requirements.txt or pyproject.toml format)
|       - Every package version-pinned
|       - Organized by layer (api, db, queue, parsing, embedding, security, observability, dev)
|     - Docker images
|       - Every image pinned to digest hash (not tag)
|       - Organized by service
|     - ML models
|       - Model name, source, version, file size, checksum
|
+-- 3. Offline Mode Dependency Manifest (TECH-03)
|     - Everything from online manifest PLUS:
|     - Local embedding model weights (Nomic, with exact file path and SHA-256)
|     - ClamAV signature database (version, date, update mechanism)
|     - PII/NER model weights (if ML-based; model name, version, SHA-256)
|     - All Docker images as saved tarballs
|     - Total bundle size estimate
|
+-- 4. Cross-Mode Compatibility Matrix
|     - For each component: online version, offline version, compatibility notes
|     - Explicit divergences documented with rationale
```

**Why this structure:** Success criterion #4 states "every component has exactly one technology choice." Success criterion #5 states "both manifests are version-pinned and include every package, Docker image, and ML model weight." The structure above ensures both criteria are met by construction.

### Pattern 3: Tenant Lifecycle State Machine

**What:** A formal state machine for tenant provisioning, operation, and deprovisioning.

**When to use:** PRD section 3 (PRD-03).

**States and transitions:**

```text
                   create_tenant()
                         |
                         v
                    +----------+
                    | PENDING  |
                    +----+-----+
                         |
                   provision()
                         |
                         v
                  +--------------+
                  | PROVISIONING |-----> FAILED (retry or manual fix)
                  +------+-------+
                         |
                    completed()
                         |
                         v
                    +--------+
          +-------->| ACTIVE |<--------+
          |         +---+----+         |
          |             |              |
     resume()    kill_switch()    update_config()
          |             |              |
          |             v              |
          |       +-----------+        |
          +-------| SUSPENDED |--------+
                  +-----------+
                       |
              deprovision()
                       |
                       v
              +----------------+
              | DEPROVISIONING |-----> FAILED (manual intervention)
              +-------+--------+
                      |
                 completed()
                      |
                      v
             +----------------+
             | DEPROVISIONED  |
             +----------------+
```

**Per-state details required for each transition:**

| Transition | Trigger | Pre-conditions | Actions | Audit Event | Rollback |
| ---------- | ------- | -------------- | ------- | ----------- | -------- |
| PENDING -> PROVISIONING | API call | Valid tenant config | Begin infrastructure creation | TENANT_PROVISION_STARTED | Delete partial resources |
| PROVISIONING -> ACTIVE | Automatic | All resources healthy | Enable API routing | TENANT_PROVISIONED | N/A |
| PROVISIONING -> FAILED | Automatic | Resource creation failed | Log failure details | TENANT_PROVISION_FAILED | Cleanup partial resources |
| ACTIVE -> SUSPENDED | API call (kill-switch) | Tenant exists | Disable routing, pause jobs, revoke API keys | TENANT_SUSPENDED | Resume |
| SUSPENDED -> ACTIVE | API call | Tenant exists | Re-enable routing, restore API keys | TENANT_RESUMED | Re-suspend |
| ACTIVE -> DEPROVISIONING | API call | Tenant exists, confirmed | Begin data deletion cascade | TENANT_DEPROVISION_STARTED | Cannot undo after data deletion |
| DEPROVISIONING -> DEPROVISIONED | Automatic | All resources deleted, data purged | Remove from registry | TENANT_DEPROVISIONED | N/A |

**Confidence: HIGH** -- Tenant lifecycle state machines are well-established in multi-tenant SaaS architecture (AWS SaaS Factory, Azure Architecture Center, SAP Architecture Center all document this pattern).

### Anti-Patterns to Avoid

- **Prose-only lifecycle description:** "Tenants are provisioned and can be suspended or deleted" -- not specific enough for implementation. Must be a formal state machine with transitions.
- **Ambiguous technology language:** "We recommend PostgreSQL or could use MySQL" -- Phase 1 success criteria require exactly one choice per component.
- **Version ranges without floors:** "Use FastAPI" without a version pin -- the manifests must be version-pinned.
- **Missing offline manifest:** Documenting only online dependencies and adding "plus local models" -- the offline manifest must be independently complete.
- **Forward references to unwritten docs:** "See the isolation architecture (Phase 2)" for details needed in the PRD -- the PRD must be self-contained for its scope.

## Don't Hand-Roll

Problems that look simple but have existing solutions. Since this phase produces documents, "don't hand-roll" means "don't write from scratch when existing artifacts exist."

| Problem | Don't Build From Scratch | Use Instead | Why |
| ------- | ------------------------ | ----------- | --- |
| Pipeline phase descriptions | Write new prose from nothing | Synthesize from `ETL_PIPELINE_PROPOSAL.md` phases A-E + `ARCHITECTURE.md` data flow diagrams | Existing artifacts contain detailed phase descriptions with inputs/outputs already specified |
| Persona definitions | Invent new personas | Reference `CUSTOMER_JOURNEY_MAP.md` Dana persona and journey map | Dana is already well-defined with pain points P1-P5 and a stage-by-stage journey |
| Threat/safety requirements | Enumerate threats from scratch | Reference `THREAT_MODEL_SAFETY.md` controls A-F | Threat model already covers boundary, ingestion, parsing, retrieval, tenancy, and audit controls |
| Data flow diagrams | Create new diagram syntax | Extend existing `diagrams/architecture.mmd` Mermaid diagram | Existing diagram covers the full pipeline flow; add per-phase detail diagrams |
| Technology rationale | Research all options again | Use `STACK.md` rationale (verified/updated in this research) | STACK.md already contains detailed "why not" analysis for every alternative considered |
| Feature requirements | Enumerate features from scratch | Map from `FEATURES.md` table-stakes features (TS-1 through TS-7) | 40+ features already categorized with dependencies and complexity ratings |
| Pitfall awareness | Discover pitfalls during planning | Reference `PITFALLS.md` phase-specific warnings table | 22 pitfalls already categorized by severity and mapped to pipeline phases |

**Key insight:** Phase 1's primary authoring task is synthesis and formalization, not original research. The source material exists across six documents. The PRD's value is in being the single, self-contained, authoritative reference -- not in containing novel information.

## Common Pitfalls

### Pitfall 1: PRD That Duplicates Instead of Synthesizes

**What goes wrong:** The PRD copies text verbatim from existing artifacts, creating a 50-page document that is redundant with ETL_PIPELINE_PROPOSAL.md, CUSTOMER_JOURNEY_MAP.md, etc. Future changes require updating multiple documents.

**Why it happens:** The instinct is to be "complete" by including everything. But completeness via duplication creates maintenance burden and inconsistency risk.

**How to avoid:** The PRD should synthesize and formalize. Where existing artifacts describe pipeline phases in prose, the PRD formalizes them with data flow diagrams, input/output schemas, and audit event specifications. The PRD is the normative document; existing artifacts become historical context.

**Warning signs:** PRD sections that are copy-paste from ETL_PIPELINE_PROPOSAL.md without added structure or specificity.

### Pitfall 2: Technology Decision Without Resolving the MinIO Question

**What goes wrong:** The tech decisions document lists MinIO as the object storage choice (copying STACK.md) without addressing the December 2025 maintenance mode announcement. An engineer reads the doc, provisions MinIO, and later discovers it receives no new features or community support.

**Why it happens:** The prior research (STACK.md) was conducted before MinIO entered maintenance mode. The recommendation was sound at the time but is now stale.

**How to avoid:** The tech decisions document must acknowledge MinIO's maintenance mode status and make a clear decision: (a) continue with MinIO (acceptable for the offline bundle where features are frozen anyway, and for near-term use), (b) switch to an alternative (Garage, SeaweedFS), or (c) use Hetzner Object Storage for online mode and MinIO only for the offline bundle. The decision must be documented with rationale.

**Warning signs:** Tech doc that says "Use MinIO" without mentioning maintenance mode.

### Pitfall 3: Embedding Dimension Mismatch Not Resolved in PRD

**What goes wrong:** The PRD specifies Nomic embed-text for offline mode and OpenRouter for online mode without resolving the dimension mismatch. Implementation proceeds with mismatched dimensions. Vectors created online cannot be queried offline or vice versa.

**Why it happens:** The dimension issue is documented in PITFALLS.md (Mod1) but the STACK.md research does not resolve it because it documents technologies individually, not their cross-mode interaction.

**How to avoid:** The PRD must specify the exact embedding model and dimension for both modes and document whether cross-mode vector compatibility is required. If compatibility is required, select models and dimensions that align. If not, document this explicitly as a product constraint.

**Warning signs:** PRD that lists "Nomic for offline, OpenRouter for online" without specifying dimensions or compatibility requirements.

### Pitfall 4: API Contracts Without Error Responses

**What goes wrong:** The API contract specification (PRD-05) defines happy-path request/response schemas but omits error responses. Implementation engineers invent ad-hoc error formats, breaking consistency and making client integration harder.

**Why it happens:** Error responses feel like implementation detail and are often deferred. But for a zero-shot PRD that enables blind implementation, the error contract is essential.

**How to avoid:** Every API endpoint definition must include: (a) success response schema, (b) validation error response schema (400), (c) auth error response (401/403), (d) not found response (404), (e) rate limit response (429), (f) internal error response (500). Use a consistent error envelope.

**Warning signs:** API spec that only shows 200 responses.

### Pitfall 5: Version Pins Without Checksum/Digest

**What goes wrong:** The dependency manifest pins versions by semantic version (e.g., `fastapi>=0.115`) but not by hash/digest. A supply chain attack replaces the package contents at the same version number. The offline bundle is compromised.

**Why it happens:** Semantic version pinning is the common practice. Hash pinning is extra work and makes updates harder. But for an offline air-gapped bundle serving regulated industries, supply chain integrity is critical.

**How to avoid:** For the online manifest, semantic version floors (>=X.Y) are acceptable. For the offline manifest (TECH-03), every package, Docker image, and model weight must include a SHA-256 hash. The offline bundle build process must verify hashes before packaging. Docker images must be pinned by digest, not tag.

**Warning signs:** Offline manifest that uses `python:3.12-slim` instead of `python:3.12-slim@sha256:...`.

## Code Examples

Not applicable -- Phase 1 produces documents, not code. However, the PRD must include schema examples for the planner to reference.

### API Error Envelope (for PRD-05)

```python
# Standard error response format for all API endpoints
# Include this in the PRD as the normative error schema
{
    "success": False,
    "error": {
        "code": "VALIDATION_ERROR",           # machine-readable error code
        "message": "File type not allowed",    # human-readable message
        "details": [                           # optional structured details
            {
                "field": "files[0].mime_type",
                "value": "application/x-executable",
                "constraint": "must be one of: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, ..."
            }
        ],
        "request_id": "req-abc123"             # correlation ID for audit trail
    }
}
```

### Intake Receipt Schema (for PRD-02)

```python
# Intake receipt produced for every file accepted at the gateway
# Include this in the PRD as the normative receipt schema
{
    "receipt_id": "uuid-v7",
    "tenant_id": "tenant_abc",
    "batch_id": "batch_xyz",
    "file_id": "file_001",
    "original_filename": "contract_2024.pdf",
    "mime_type": "application/pdf",
    "size_bytes": 2457600,
    "sha256": "a1b2c3d4...",
    "scan_result": "clean",                   # clean | quarantined | skipped
    "received_at": "2026-02-08T14:30:00Z",
    "storage_path": "raw/tenant_abc/file_001/a1b2c3d4",
    "status": "accepted"                      # accepted | rejected | quarantined
}
```

### Audit Event Schema (for PRD-02/PRD-04)

```python
# Every pipeline step emits an audit event in this format
# Include this in the PRD as the normative audit event schema
{
    "event_id": "uuid-v7",
    "tenant_id": "tenant_abc",
    "event_type": "DOCUMENT_INGESTED",         # enum of defined event types
    "timestamp": "2026-02-08T14:30:00Z",       # UTC ISO 8601, always
    "actor": "system",                         # system | user_id
    "resource_type": "document",               # document | chunk | query | tenant
    "resource_id": "file_001",
    "details": {
        "component": "intake-gateway",
        "input_hash": "sha256:...",
        "output_hash": "sha256:...",
        "pipeline_version": "1.0.0",
        "duration_ms": 234,
        "status": "success"                    # success | failure | quarantined
    },
    "previous_event_id": null                  # for lineage chain
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact on Phase 1 |
| ------------ | ----------------- | ------------ | ----------------- |
| MinIO community (actively developed) | MinIO community (maintenance mode) | Dec 2025 | Tech decisions must address this; evaluate Garage or SeaweedFS |
| Prometheus 2.x | Prometheus 3.x (current) | 2024 | Update version pins from >=2.54 to >=3.5 |
| Nomic embed-text v1 | Nomic embed-text v1.5 (stable) / v2 MoE (new, local TBD) | v1.5: 2024, v2: late 2025 | Lock to v1.5 for offline (confirmed local inference); consider v2 when Ollama support confirmed |
| Redis 7.x | Redis 8.x (GA) | 2025/2026 | Update version pins |
| Celery 5.4 | Celery 5.6 (memory leak fixes) | 2025/2026 | Update version pins; 5.6 is strongly recommended |
| Qdrant basic multitenancy | Qdrant 1.16 tiered multitenancy | Nov 2025 | Tiered multitenancy enables single-collection approach with tenant promotion -- update architecture recommendation |
| Pydantic 2.9 | Pydantic 2.12 | 2025/2026 | Update version pins; note Python 3.14 support |
| SQLAlchemy greenlet auto-install | SQLAlchemy asyncio requires explicit install target | 2025/2026 | Must use `sqlalchemy[asyncio]` in requirements |

**Deprecated/outdated from STACK.md:**

- MinIO community as "actively developed" -- now in maintenance mode
- Prometheus 2.x version range -- Prometheus 3.x is current
- Nomic embed-text v1 as the only option -- v1.5 is the stable local choice, v2 exists but local support pending

## Open Questions

Things that require product decisions and cannot be resolved by research alone. These must be resolved during plan execution.

### 1. MinIO Maintenance Mode: Continue or Switch?

**What we know:**

- MinIO community edition entered maintenance mode in December 2025
- No new features, PRs, or enhancements will be accepted
- Security fixes evaluated "case by case"
- Web management console was already removed from community edition (Feb 2025)
- The S3 API implementation is stable and feature-complete for this use case
- Alternatives exist: Garage (Rust, Apache 2.0, v2.0), SeaweedFS (Go, Apache 2.0), Hetzner Object Storage (online only)

**What's unclear:**

- Whether MinIO's maintenance mode will lead to eventual archival
- Whether the "case by case" security fix policy is acceptable for regulated deployments
- Whether Garage v2.0 is mature enough for production use in regulated environments

**Recommendation:** Make one of these decisions in the tech document:

- **Option A (pragmatic):** Continue with MinIO. The S3 API is stable, the codebase is mature, and for a planning pack this is the lowest-risk choice. Document the maintenance mode status and note Garage as the migration target if MinIO is abandoned entirely.
- **Option B (forward-looking):** Switch to Garage for the long-term recommendation. Document MinIO as acceptable for initial deployment with a migration plan to Garage.
- **Option C (split):** Use Hetzner Object Storage for online mode, MinIO for offline bundle only. Minimizes the surface area of the maintenance-mode dependency.

**Confidence: MEDIUM** -- This is a product/risk decision, not a technical one. All three options are defensible.

### 2. Embedding Dimension Alignment Across Modes

**What we know:**

- Nomic embed-text v1.5: 768 dimensions (configurable down to 64 via Matryoshka)
- Nomic embed-text v2 MoE: 768 dimensions (configurable to 256)
- OpenRouter `openai/text-embedding-3-small`: 1536 dimensions (configurable)
- OpenRouter `openai/text-embedding-3-large`: 3072 dimensions (configurable)
- OpenRouter `text-embedding-3-small` supports dimension reduction via the API

**What's unclear:**

- Whether the project requires cross-mode vector compatibility (can an offline-created index be queried in online mode?)
- If dimension reduction on OpenRouter models to 768d provides acceptable retrieval quality

**Recommendation:** Lock both modes to 768 dimensions:

- Offline: Nomic embed-text v1.5 at native 768d
- Online: OpenRouter `text-embedding-3-small` with `dimensions: 768` parameter (OpenAI models support this)
- This enables cross-mode vector compatibility if needed
- Document that switching to v2 Nomic or different OpenRouter models requires full re-indexing

### 3. Nomic v1.5 vs v2 for Offline Mode

**What we know:**

- v1.5: Confirmed local inference via GPT4All, supports CPU and GPU, well-tested
- v2 MoE: Better quality (esp. multilingual), but Ollama local inference support announced as "coming soon" with no confirmed date
- v1.5 GGUF quantized versions available for resource-constrained environments

**What's unclear:**

- v2 Ollama release timeline
- v2 local inference performance characteristics (475M params, MoE routing overhead)
- Whether v2 CPU-only performance is acceptable for offline bundle use

**Recommendation:** Lock to Nomic embed-text v1.5 for the planning pack. v1.5 is confirmed working for local inference. Document v2 as a future upgrade path when local inference is confirmed. The planning pack must be executable now, not dependent on unreleased features.

### 4. Qdrant: Collection-Per-Tenant vs Tiered Multitenancy (1.16)

**What we know:**

- ARCHITECTURE.md recommends collection-per-tenant
- Qdrant 1.16 (released Nov 2025) introduces tiered multitenancy: shared fallback shard for small tenants, dedicated shards for large tenants via "promotion"
- Qdrant docs recommend starting with single-collection payload-based multitenancy and promoting large tenants
- For Frostbyte, per-tenant isolation is a hard requirement

**What's unclear:**

- Whether tiered multitenancy provides sufficient isolation for regulated workloads (payload-based filtering in shared shard could leak data on filter misconfiguration)
- Whether collection-per-tenant introduces unacceptable resource overhead

**Recommendation:** Maintain collection-per-tenant for the PRD. Frostbyte's isolation-by-construction principle means shared shards (even with payload filtering) are unacceptable for regulated tenants. The tiered multitenancy feature is relevant for a future "shared infrastructure" tier, not for the core regulated offering. Document this decision with rationale in the tech document.

## Existing Artifact Inventory

What the planner can draw from vs. what must be written fresh.

### Available for Synthesis (existing content to formalize)

| Artifact | Location | What It Provides for Phase 1 |
| -------- | -------- | ---------------------------- |
| ETL_PIPELINE_PROPOSAL.md | `docs/` | Executive summary draft, pipeline phases A-E, acceptance criteria, deployment modes |
| CUSTOMER_JOURNEY_MAP.md | `docs/` | Dana persona, pain points P1-P5, journey stages with required artifacts |
| THREAT_MODEL_SAFETY.md | `docs/` | Security controls A-F, primary risks |
| architecture.mmd | `diagrams/` | Pipeline flow diagram (intake -> normalization -> policy -> storage -> serving) |
| tenancy.mmd | `diagrams/` | Control plane -> tenant data plane -> audit store topology |
| offline_bundle.mmd | `diagrams/` | Offline Docker Compose service diagram |
| VENDOR_ACCEPTANCE_REPORT.md | `templates/` | Report template (intake, parsing, classification, indexing results) |
| STACK.md | `.planning/research/` | Technology selection with rationale for every component |
| FEATURES.md | `.planning/research/` | 40+ features categorized (table stakes, differentiators, anti-features) |
| ARCHITECTURE.md | `.planning/research/` | Full architecture: control/data/audit planes, component boundaries, data flow, storage patterns |
| PITFALLS.md | `.planning/research/` | 22 pitfalls by severity, mapped to pipeline phases and Dana's pain points |

### Must Be Written Fresh (not covered by existing artifacts)

| Content | Requirement | Why It Does Not Exist Yet |
| ------- | ----------- | ------------------------- |
| Tenant lifecycle state machine | PRD-03 | ETL_PIPELINE_PROPOSAL mentions kill-switch but does not define states/transitions |
| Per-phase data flow diagrams with I/O schemas | PRD-02 | architecture.mmd shows the macro flow; per-phase diagrams with typed inputs/outputs do not exist |
| API contract specification (endpoints, schemas, errors) | PRD-05 | No API spec exists anywhere in the project |
| Monitoring/alerting requirements specification | PRD-04 | STACK.md lists Prometheus/Grafana/Loki but no alerting rules, metric definitions, or dashboard specs |
| Version-pinned online dependency manifest | TECH-02 | STACK.md has version ranges, not a complete pinned manifest |
| Version-pinned offline dependency manifest | TECH-03 | Does not exist; must include model weights, ClamAV sigs, all Docker images |
| Finalized component decision table (one choice per component) | TECH-01 | STACK.md is exploratory ("recommendation" + "alternative"); must be collapsed to decisions |
| Cross-mode compatibility documentation | TECH-01 | No document explicitly addresses online/offline parity at the dependency level |

## Sources

### Primary (HIGH confidence)

- Project artifacts: `docs/ETL_PIPELINE_PROPOSAL.md`, `docs/CUSTOMER_JOURNEY_MAP.md`, `docs/THREAT_MODEL_SAFETY.md`, `diagrams/*.mmd`, `templates/VENDOR_ACCEPTANCE_REPORT.md` -- read in full
- Prior research: `.planning/research/STACK.md`, `.planning/research/FEATURES.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md` -- read in full
- Project state: `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md` -- read in full

### Secondary (MEDIUM confidence -- WebSearch verified against official sources)

- [FastAPI PyPI](https://pypi.org/project/fastapi/) -- version currency confirmed
- [FastAPI GitHub Releases](https://github.com/fastapi/fastapi/releases) -- actively maintained, Starlette >=0.40 supported
- [Pydantic PyPI](https://pypi.org/project/pydantic/) -- v2.12.5 confirmed, Python 3.14 support
- [SQLAlchemy GitHub Releases](https://github.com/sqlalchemy/sqlalchemy/releases) -- v2.0.46 stable, asyncio greenlet change noted
- [Celery PyPI](https://pypi.org/project/celery/) -- v5.6.2 confirmed, memory leak fixes
- [Celery Docs](https://docs.celeryq.dev/en/stable/getting-started/index.html) -- Python 3.9-3.13 support
- [Redis GitHub Releases](https://github.com/redis/redis/releases) -- v8.4 GA confirmed
- [Qdrant Blog v1.16](https://qdrant.tech/blog/qdrant-1.16.x/) -- tiered multitenancy confirmed
- [Qdrant Multitenancy Docs](https://qdrant.tech/documentation/guides/multitenancy/) -- best practices for tenant isolation
- [Docling PyPI](https://pypi.org/project/docling/) -- v2.72.0 confirmed, Python >=3.10
- [Unstructured PyPI](https://pypi.org/project/unstructured/) -- latest release 2026-01-27 confirmed
- [Nomic v2 Hugging Face](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe) -- 768d, MoE architecture confirmed
- [Nomic v1.5 Hugging Face](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) -- 768d, Matryoshka, local inference confirmed
- [Nomic Blog v2](https://www.nomic.ai/blog/posts/nomic-embed-text-v2) -- Ollama "coming soon" noted
- [Prometheus GitHub Releases](https://github.com/prometheus/prometheus/releases) -- v3.9.1 confirmed
- [structlog PyPI](https://pypi.org/project/structlog/) -- v25.5.0 confirmed
- [hcloud PyPI](https://pypi.org/project/hcloud/) -- v2.16.0 confirmed
- [MinIO InfoQ maintenance mode](https://www.infoq.com/news/2025/12/minio-s3-api-alternatives/) -- maintenance mode confirmed Dec 2025
- [MinIO alternatives blog](https://blog.elest.io/minio-is-in-maintenance-mode-your-guide-to-s3-compatible-storage-alternatives/) -- Garage, SeaweedFS, Ceph RGW as alternatives
- [OpenRouter Embeddings API](https://openrouter.ai/docs/api/reference/embeddings) -- OpenAI-compatible API confirmed
- [Azure Tenant Lifecycle](https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/tenant-life-cycle) -- tenant lifecycle patterns
- [SAP Tenant Lifecycle](https://architecture.learning.sap.com/docs/ref-arch/d31bedf420/3) -- provisioning/deprovisioning patterns

### Tertiary (LOW confidence -- training data only)

- Tenant lifecycle state machine patterns -- based on established SaaS architecture knowledge, not verified against a specific 2026 source
- API contract best practices for multi-tenant systems -- general REST API design knowledge

## Metadata

**Confidence breakdown:**

- Verified version pins: HIGH -- all checked against PyPI/GitHub on 2026-02-08
- PRD structure patterns: HIGH -- derived from success criteria + standard PRD practices
- Technology decision finalization: MEDIUM -- MinIO status creates an open question requiring product decision
- Tenant lifecycle state machine: HIGH -- well-established pattern, multiple authoritative references
- Embedding dimension analysis: HIGH -- dimensions verified against Hugging Face model cards and OpenRouter docs
- API contract patterns: MEDIUM -- standard REST patterns, not verified against a specific multi-tenant ETL reference

**Research date:** 2026-02-08
**Valid until:** 2026-03-08 (30 days -- stable domain, but MinIO situation may evolve)
