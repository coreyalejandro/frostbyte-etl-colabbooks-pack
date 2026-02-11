# Plan 01-01 Summary: Zero-Shot PRD

## Plan

- **Phase:** 01 — Product Definition and Tech Decisions
- **Plan:** 01-01 — Zero-Shot PRD
- **Status:** Complete
- **Artifact:** `docs/PRD.md`

## What Was Done

Created the comprehensive Product Requirements Document (PRD) for the Frostbyte multi-tenant ETL pipeline. The document is self-contained: an engineer reading only `docs/PRD.md` can describe the full pipeline lifecycle, identify all personas, explain the tenant lifecycle state machine, reference concrete API contracts, and understand monitoring requirements.

### Artifact Details

| Metric | Value |
|--------|-------|
| Lines | 3108 |
| Sections | 5 main sections + Document Conventions + Glossary + 8 Appendices |
| Mermaid diagrams | 7 (1 architecture overview + 5 pipeline phases + 1 state machine) |
| API endpoints defined | 17 across 4 endpoint groups |
| Metrics defined | 20 concrete metric names |
| Alert conditions defined | 12 with severity levels and thresholds |
| Tenant states defined | 7 with complete transition table |
| Audit event types defined | 24 across all pipeline phases and tenant lifecycle |

### Section Summary

**Section 1: Executive Summary (PRD-01)**

- What/Why/Who/How with three-tier architecture diagram
- Four personas: Dana (Vendor Data Ops Lead), Frode (Platform Owner), Engineers, Auditors
- Deployment modes: online (cloud) and offline (air-gapped Docker)
- Anti-features table: 6 explicitly excluded features with rationale

**Section 2: Pipeline Phase Specifications (PRD-02)**

- Phase A: Intake Gateway — manifest validation, MIME check, checksum verification, malware scan, receipt generation
- Phase B: Document Normalization — two-stage parsing (layout + chunking), canonical JSON schema with deterministic chunk IDs
- Phase C: Policy Gates — PII detection, document classification, injection defense (all run before embedding)
- Phase D: Embedding and Storage — 768d vectors, three-store write pattern, integrity verification
- Phase E: Serving — RAG retrieval with provenance, cite-only-from-retrieval enforcement

**Section 3: Tenant Lifecycle Management (PRD-03)**

- State machine with 7 states: PENDING, PROVISIONING, ACTIVE, SUSPENDED, DEPROVISIONING, DEPROVISIONED, FAILED
- 13 state transitions with triggers, pre-conditions, actions, audit events, and rollback
- Kill-switch specification: instant (< 1s routing disable) and reversible
- Provisioning sequence: 11 steps from project creation to health verification
- Deprovisioning cascade: 10 steps with verification at each stage

**Section 4: Monitoring and Observability (PRD-04)**

- Job tracking with per-file, per-stage granularity
- 20 concrete metric names (counters, histograms, gauges)
- 12 alert conditions with severity (CRITICAL/HIGH/MEDIUM/LOW), thresholds, and actions
- Structured JSON log requirements with mandatory fields and content rules
- Dashboard specifications for per-tenant and platform-wide views

**Section 5: API Contract Specification (PRD-05)**

- 17 endpoints across Intake (3), Query (3), Admin (7), and Audit (4) groups
- Standard error envelope with machine-readable codes
- Full request/response schemas with field descriptions
- Error responses (400, 401, 403, 404, 409, 429, 500, 503) for every endpoint
- JWT-based auth with role-endpoint mapping
- Rate limits per endpoint group

**Appendices:**

- A: Complete audit event type reference (24 event types)
- B: Cross-reference matrix (audit events to APIs, transitions to endpoints, metrics to phases, personas to endpoints)
- C: Document format allowlist with explicitly unsupported formats
- D: Retry and idempotency policies per pipeline stage
- E: Deployment mode comparison matrix
- F: Data schema summary with pipeline data flow
- G: Tenant configuration reference with field validation rules
- H: Acceptance report specification

## Verification Results

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Top-level sections | >= 5 | 15 | PASS |
| Mermaid diagrams | >= 6 | 7 | PASS |
| All 7 tenant states present | 7 | 7 | PASS |
| Line count | > 3000 | 3108 | PASS |
| No ambiguous tech language | 0 | 0 | PASS |
| 4 personas identified | 4 | 4 | PASS |
| Each phase has I/O/diagram/errors/audit | 5/5 | 5/5 | PASS |
| Transition table with required columns | Yes | Yes | PASS |
| API endpoints with full schemas | Yes | Yes | PASS |
| Concrete metric names | Yes | 20 defined | PASS |
| No implementation details leaked | Yes | Yes | PASS |
| Glossary exists | Yes | Yes (15 terms) | PASS |
| Anti-features table present | Yes | Yes (6 items) | PASS |
| No forward references to unwritten docs | Yes | Yes | PASS |

## Source Materials Synthesized

| Source | What Was Synthesized |
|--------|---------------------|
| `docs/ETL_PIPELINE_PROPOSAL.md` | Pipeline phases A-E, executive summary, deployment modes, acceptance criteria |
| `docs/CUSTOMER_JOURNEY_MAP.md` | Dana persona, pain points P1-P5, journey stages |
| `docs/THREAT_MODEL_SAFETY.md` | Security controls A-F, injection defense, cite-only-from-retrieval |
| `.planning/research/ARCHITECTURE.md` | Three-tier architecture, component boundaries, data flow, provisioning sequence, storage patterns |
| `.planning/research/FEATURES.md` | Table stakes features, anti-features AF-1 through AF-6, feature dependencies |
| `.planning/research/PITFALLS.md` | Error handling patterns, idempotency requirements, monitoring needs |
| `.planning/phases/01-.../01-RESEARCH.md` | Verified version pins, embedding dimension alignment (768d), intake receipt schema, error envelope, tenant state machine pattern |
| `diagrams/*.mmd` | Architecture, tenancy, and offline bundle diagrams (synthesized into Mermaid within PRD) |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Lock both modes to 768d embeddings | Enables cross-mode vector compatibility. Online mode configures API with `dimensions: 768`; offline uses native 768d model. |
| Policy gates run before embedding (hard constraint) | Malicious or sensitive content must never reach the vector store. Referenced from ARCHITECTURE.md anti-pattern #2. |
| Cite-only-from-retrieval is architectural, not prompt engineering | Every claim in generated answers must reference a chunk_id from retrieval proof. Ungrounded text is flagged or suppressed. |
| Per-tenant vector collections, not shared index with filtering | Filter-based isolation is fragile; one missing filter leaks cross-tenant data. Physical isolation by construction. |
| Deterministic chunk IDs via content+position hash | Enables idempotent reprocessing, stable audit trails, and duplicate detection across re-runs. |

## Commits

| Hash | Message |
|------|---------|
| `f2b6d3f` | `feat(01-01): write zero-shot PRD` |
