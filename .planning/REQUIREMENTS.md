# Requirements: Frostbyte ETL Planning Pack

**Defined:** 2026-02-08
**Core Value:** Every planning artifact must be so specific and deterministic that a person who has never seen the codebase could build, deploy, support, and explain the system by following the documents alone.

## v1 Requirements

Requirements for milestone v1.0: Zero-Shot Implementation Pack. Each maps to roadmap phases.

### PRD — Product Requirements Document

- [x] **PRD-01**: Executive summary of the multi-tenant ETL pipeline (what, why, who, how)
- [x] **PRD-02**: Pipeline phase specifications (intake, parsing, enrichment, storage, serving) with data flow diagrams
- [x] **PRD-03**: Tenant lifecycle management specification (provisioning, configuration, deprovisioning, kill-switch)
- [x] **PRD-04**: Monitoring and observability requirements (job tracking, alerting, metrics)
- [x] **PRD-05**: API contract specification (intake, query, admin, audit endpoints)

### TECH — Technology Decisions

- [x] **TECH-01**: Component-by-component tech selection with rationale (parser, embedder, stores, queue, gateway)
- [x] **TECH-02**: Version-pinned dependency manifest for online mode
- [x] **TECH-03**: Version-pinned dependency manifest for offline mode (local models, ClamAV signatures)

### IMPL — Implementation Plans

- [x] **IMPL-01**: Foundation layer plan (tenant data model, config framework, Docker skeleton, audit schema)
- [x] **IMPL-02**: Storage layer plan (MinIO, PostgreSQL, Qdrant, Redis per-tenant provisioning)
- [x] **IMPL-03**: Intake gateway plan (auth, manifest, checksum, malware scan, receipts)
- [x] **IMPL-04**: Parsing pipeline plan (Docling + Unstructured orchestration, canonical JSON schema)
- [x] **IMPL-05**: Policy engine plan (PII detection, classification, injection defense, chunking)
- [x] **IMPL-06**: Embedding and indexing plan (OpenRouter online, Nomic offline, vector writes)
- [x] **IMPL-07**: Serving layer plan (RAG API, retrieval proofs, cite-only-from-retrieval)

### ISOL — Tenant Isolation Architecture

- [ ] **ISOL-01**: Hetzner Cloud provisioning specification (servers, networks, firewalls, volumes per tenant)
- [ ] **ISOL-02**: Per-tenant storage namespace design (object, relational, vector isolation)
- [ ] **ISOL-03**: Per-tenant encryption key management design (KMS, envelope encryption, rotation)
- [ ] **ISOL-04**: Network boundary specification (VPC rules, firewall rules, cross-tenant denial)

### DEPLOY — Deployment Plans

- [x] **DEPLOY-01**: Online mode deployment architecture (Hetzner topology, scaling, HA)
- [x] **DEPLOY-02**: Offline air-gapped Docker bundle specification (compose, images, models, scripts)
- [x] **DEPLOY-03**: Mode parity matrix (what works where, explicit divergences)
- [x] **DEPLOY-04**: Offline update cycle specification (signed bundles, verification, zero-downtime cutover)

### ONBOARD — Engineer Onboarding

- [x] **ONBOARD-01**: Architecture walkthrough tutorial (control plane, data plane, audit plane)
- [x] **ONBOARD-02**: Local development environment setup guide (Docker, dependencies, test data)
- [x] **ONBOARD-03**: First-task guide (add a new document type to the pipeline, end-to-end)

### USERDOC — User Documentation (Dana Persona)

- [x] **USERDOC-01**: Vendor data operations guide (batch submission, manifest format, authentication)
- [x] **USERDOC-02**: Acceptance report interpretation guide (what each field means, common issues)
- [x] **USERDOC-03**: Troubleshooting guide (common errors, resolution steps, escalation paths)

### SCENARIO — Role-Playing Scenarios

- [x] **SCENARIO-01**: Customer success scenarios (3+ situations: onboarding questions, batch failures, compliance inquiries)
- [x] **SCENARIO-02**: Deployed engineer scenarios (3+ situations: parse failures, tenant provisioning issues, audit queries)

### AUDIT — Audit Stream Design

- [x] **AUDIT-01**: Audit event schema specification (event types, fields, hash chain design)
- [x] **AUDIT-02**: Immutable storage design (append-only guarantees, tamper evidence)
- [x] **AUDIT-03**: Query patterns and export specification (auditor workflows, SIEM integration)

### SAFETY — Document Safety Controls

- [x] **SAFETY-01**: Injection defense specification (pattern scanning, heuristic scoring, quarantine rules)
- [x] **SAFETY-02**: Content boundary enforcement design (envelope pattern, content/control separation)
- [x] **SAFETY-03**: File-type allowlisting and MIME verification specification

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Advanced Governance

- **GOV-01**: Configurable policy-as-code governance (versioned YAML/JSON policy files per tenant)
- **GOV-02**: Data residency enforcement (provable geographic constraints)
- **GOV-03**: Automated compliance evidence generation (SOC 2 / ISO 27001 / GDPR artifacts)
- **GOV-04**: Retention policy enforcement with cascading deletion receipts

### Advanced Pipeline Features

- **PIPE-01**: Parse preview with diff (human-in-the-loop verification before commit)
- **PIPE-02**: Schema evolution and migration strategy
- **PIPE-03**: Quality scoring per document (completeness, confidence metrics)
- **PIPE-04**: Configurable parser chaining (route by document type/quality)

### Vendor Onboarding Workflow

- **VENDOR-01**: Sandbox tenant for trial submissions
- **VENDOR-02**: Automated format compatibility testing
- **VENDOR-03**: Interactive vendor intake checklist

### Self-Service

- **SELF-01**: Self-service tenant status dashboard (Dana persona)
- **SELF-02**: Retrieval proof objects for RAG answers

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Production code | This is a planning pack, not a build |
| CI/CD pipeline configuration | Infrastructure automation is implementation, not planning |
| Pricing or commercial terms | Technical deliverable only |
| Cross-tenant analytics | Explicitly excluded per Frode's security posture (anti-feature AF-1) |
| Real-time streaming ingestion | Batch-first pipeline per original sketch (anti-feature AF-4) |
| LLM-in-the-loop parsing | Non-deterministic, breaks audit trails (anti-feature AF-2) |
| Shared vector index with filtering | Fragile isolation, fails security reviews (anti-feature AF-3) |
| Auto-correction of parse errors | Creates liability in legal contexts (anti-feature AF-5) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PRD-01 | Phase 1 | Complete |
| PRD-02 | Phase 1 | Complete |
| PRD-03 | Phase 1 | Complete |
| PRD-04 | Phase 1 | Complete |
| PRD-05 | Phase 1 | Complete |
| TECH-01 | Phase 1 | Complete |
| TECH-02 | Phase 1 | Complete |
| TECH-03 | Phase 1 | Complete |
| IMPL-01 | Phase 4 | Complete |
| IMPL-02 | Phase 4 | Complete |
| IMPL-03 | Phase 5 | Complete |
| IMPL-04 | Phase 5 | Complete |
| IMPL-05 | Phase 6 | Complete |
| IMPL-06 | Phase 6 | Complete |
| IMPL-07 | Phase 6 | Complete |
| ISOL-01 | Phase 2 | Pending |
| ISOL-02 | Phase 2 | Pending |
| ISOL-03 | Phase 2 | Pending |
| ISOL-04 | Phase 2 | Pending |
| DEPLOY-01 | Phase 7 | Complete |
| DEPLOY-02 | Phase 7 | Complete |
| DEPLOY-03 | Phase 7 | Complete |
| DEPLOY-04 | Phase 7 | Complete |
| ONBOARD-01 | Phase 8 | Complete |
| ONBOARD-02 | Phase 8 | Complete |
| ONBOARD-03 | Phase 8 | Complete |
| USERDOC-01 | Phase 8 | Complete |
| USERDOC-02 | Phase 8 | Complete |
| USERDOC-03 | Phase 8 | Complete |
| SCENARIO-01 | Phase 8 | Complete |
| SCENARIO-02 | Phase 8 | Complete |
| AUDIT-01 | Phase 3 | Complete |
| AUDIT-02 | Phase 3 | Complete |
| AUDIT-03 | Phase 3 | Complete |
| SAFETY-01 | Phase 3 | Complete |
| SAFETY-02 | Phase 3 | Complete |
| SAFETY-03 | Phase 3 | Complete |

**Coverage:**

- v1 requirements: 37 total
- Mapped to phases: 37
- Unmapped: 0

---
*Requirements defined: 2026-02-08*
*Last updated: 2026-02-11 after Phase 8 completion — All 37 v1 requirements complete*
