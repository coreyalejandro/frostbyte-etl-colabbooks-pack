# Roadmap: Frostbyte ETL Planning Pack

## Overview

This roadmap delivers the v1.0 Zero-Shot Implementation Pack: a complete, deterministic planning package that enables any engineer or AI agent to build, deploy, support, and explain Frostbyte's multi-tenant ETL pipeline without ambiguity. The 37 requirements span product definition, architecture, implementation plans, deployment specs, and team readiness docs. Phases are ordered by dependency: product definition and tech decisions first, then cross-cutting architecture (isolation, audit, safety), then pipeline implementation plans layer-by-layer, then deployment, and finally team-facing documentation that references everything before it.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Product Definition and Tech Decisions** - PRD and locked-in technology choices that every subsequent document references
- [ ] **Phase 2: Tenant Isolation Architecture** - Per-tenant isolation specifications (Hetzner, storage, encryption, network)
- [x] **Phase 3: Audit Stream and Document Safety** - Cross-cutting security and compliance designs that inform all implementation plans
- [x] **Phase 4: Foundation and Storage Layer Plans** - Implementation plans for the tenant data model, config framework, and per-tenant storage provisioning
- [x] **Phase 5: Intake and Parsing Pipeline Plans** - Implementation plans for the intake gateway and document parsing pipeline
- [ ] **Phase 6: Policy, Embedding, and Serving Layer Plans** - Implementation plans for the policy engine, embedding service, and RAG serving layer
- [ ] **Phase 7: Deployment Architecture** - Online and offline deployment specifications, mode parity, and update cycles
- [ ] **Phase 8: Team Readiness Documentation** - Engineer onboarding, user guides for Dana, and role-playing scenarios for CS and engineering

## Phase Details

### Phase 1: Product Definition and Tech Decisions

**Goal**: A complete PRD and locked-in technology manifest exist so that every subsequent document can reference concrete product specifications and tool choices without ambiguity
**Depends on**: Nothing (first phase)
**Requirements**: PRD-01, PRD-02, PRD-03, PRD-04, PRD-05, TECH-01, TECH-02, TECH-03
**Success Criteria** (what must be TRUE):

  1. An engineer reading only the PRD can describe the full pipeline lifecycle (intake through serving), identify all personas, and explain the monitoring/observability requirements without consulting any other document
  2. Every pipeline phase (intake, parsing, enrichment, storage, serving) has a data flow diagram showing inputs, outputs, and transformations
  3. The tenant lifecycle (provisioning, configuration, deprovisioning, kill-switch) is specified with enough detail that an engineer could implement the state machine
  4. Every component in the system (parser, embedder, stores, queue, gateway, scanner, secrets manager) has exactly one technology choice with a rationale -- no "choose between X and Y" language remains
  5. Both online and offline dependency manifests are version-pinned and include every Python package, Docker image, and ML model weight required for each mode
**Plans**: 2 plans

Plans:

- [x] 01-01-PLAN.md — Zero-shot PRD (executive summary, pipeline phases, tenant lifecycle, monitoring, API contracts)
- [x] 01-02-PLAN.md — Technology decisions and version-pinned dependency manifests

### Phase 2: Tenant Isolation Architecture

**Goal**: Per-tenant isolation is fully specified across compute, storage, network, and encryption layers so that implementation plans can reference concrete provisioning sequences and isolation evidence
**Depends on**: Phase 1
**Requirements**: ISOL-01, ISOL-02, ISOL-03, ISOL-04
**Success Criteria** (what must be TRUE):

  1. The Hetzner provisioning specification includes a step-by-step sequence (server, network, firewall, volume creation) with specific API calls, parameters, and expected responses
  2. For every stateful component (object store, relational DB, vector store, cache, logs), the document specifies the isolation mechanism, credential scope, and verification method
  3. The encryption key management design covers key generation, envelope encryption, rotation procedure, and key-to-tenant mapping -- with enough detail to implement without interpretation
  4. Network boundary rules are specified as concrete firewall rules (allow/deny, source, destination, port) for both Hetzner Cloud and Docker network modes
**Plans**: 2 plans

Plans:

- [ ] 02-01-PLAN.md -- Hetzner provisioning specification and network boundaries (ISOL-01, ISOL-04)
- [ ] 02-02-PLAN.md -- Per-tenant storage namespace and encryption key management design (ISOL-02, ISOL-03)

### Phase 3: Audit Stream and Document Safety

**Goal**: The immutable audit stream design and document safety controls are specified as standalone architecture documents that every implementation plan can reference for event emission patterns, schema compliance, and content safety gates
**Depends on**: Phase 1
**Requirements**: AUDIT-01, AUDIT-02, AUDIT-03, SAFETY-01, SAFETY-02, SAFETY-03
**Success Criteria** (what must be TRUE):

  1. The audit event schema includes concrete field definitions, event types, and a hash chain design that an engineer could implement as a database migration
  2. The immutable storage design specifies the append-only mechanism (triggers, grants, or storage engine), tamper evidence approach, and the exact PostgreSQL DDL or equivalent
  3. Audit query patterns cover the three primary auditor workflows (by tenant, by document, by time range) with example queries and export format specification
  4. Injection defense is specified with concrete regex patterns, heuristic scoring thresholds, quarantine rules, and the decision tree for pass/flag/quarantine
  5. The content boundary enforcement (envelope pattern) is specified with data structure examples showing how content and control metadata are separated at every pipeline stage
**Plans**: TBD

Plans:

- [x] 03-01: Audit event schema, immutable storage design, and query patterns
- [x] 03-02: Injection defense, content boundary enforcement, and file-type allowlisting

### Phase 4: Foundation and Storage Layer Plans

**Goal**: Step-by-step implementation plans exist for the foundational data model and per-tenant storage provisioning, detailed enough that an engineer can execute them without asking clarifying questions
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: IMPL-01, IMPL-02
**Success Criteria** (what must be TRUE):

  1. The foundation layer plan specifies the tenant data model schema, configuration framework (env vars, secrets, feature flags), Docker Compose skeleton, and audit event emission pattern for the foundation layer
  2. The storage layer plan specifies MinIO bucket provisioning, PostgreSQL database provisioning, Qdrant collection provisioning, and Redis setup -- all with per-tenant credential generation and isolation verification steps
  3. Both plans reference the Phase 2 isolation architecture and Phase 3 audit schema by specific section, not by vague allusion
**Plans**: 2 plans

Plans:

- [x] 04-01: Foundation layer implementation plan (docs/FOUNDATION_LAYER_PLAN.md)
- [x] 04-02: Storage layer implementation plan (docs/STORAGE_LAYER_PLAN.md)

### Phase 5: Intake and Parsing Pipeline Plans

**Goal**: Step-by-step implementation plans exist for the intake gateway (trust boundary) and parsing pipeline (Docling + Unstructured), covering the full request flow from vendor upload to canonical structured document JSON
**Depends on**: Phase 4
**Requirements**: IMPL-03, IMPL-04
**Success Criteria** (what must be TRUE):

  1. The intake gateway plan specifies the full request flow (auth, manifest validation, checksum, MIME check, malware scan, object store write, receipt generation, audit event, job enqueue) with API endpoint definitions and error response formats
  2. The parsing pipeline plan specifies Docling + Unstructured orchestration, canonical JSON schema with field definitions, lineage pointer structure, and parse failure reporting -- with enough detail to write the canonical schema as a Pydantic model
  3. Both plans include the audit event types they emit, referencing the Phase 3 audit schema
**Plans**: 2 plans

Plans:

- [x] 05-01: Intake gateway implementation plan (docs/INTAKE_GATEWAY_PLAN.md)
- [x] 05-02: Parsing pipeline implementation plan (docs/PARSING_PIPELINE_PLAN.md)

### Phase 6: Policy, Embedding, and Serving Layer Plans

**Goal**: Step-by-step implementation plans exist for the policy engine (PII, classification, injection defense), embedding service (online + offline), and RAG serving layer (retrieval with provenance), completing the full pipeline specification
**Depends on**: Phase 5
**Requirements**: IMPL-05, IMPL-06, IMPL-07
**Success Criteria** (what must be TRUE):

  1. The policy engine plan specifies PII detection rules, classification categories and routing logic, injection defense integration (referencing Phase 3 safety specs), and deterministic chunking with stable ID generation
  2. The embedding plan specifies both OpenRouter (online) and Nomic (offline) integration, including model version recording, dimension assertions, and the vector write flow to Qdrant
  3. The serving layer plan specifies the RAG retrieval flow, retrieval proof object schema, cite-only-from-retrieval enforcement mechanism, and the query-to-response lifecycle with audit event emission
  4. All three plans handle both online and offline mode differences explicitly
**Plans**: TBD

Plans:

- [ ] 06-01: Policy engine implementation plan
- [ ] 06-02: Embedding and indexing implementation plan
- [ ] 06-03: Serving layer (RAG API) implementation plan

### Phase 7: Deployment Architecture

**Goal**: Complete deployment specifications exist for both online (Hetzner) and offline (air-gapped Docker) modes, including the mode parity matrix and offline update cycle, so that an ops engineer can deploy the system in either mode
**Depends on**: Phase 2, Phase 6
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04
**Success Criteria** (what must be TRUE):

  1. The online deployment architecture specifies Hetzner topology (server types, network layout, load balancer config, scaling approach, HA strategy) with a concrete provisioning runbook
  2. The offline Docker bundle specification includes the complete docker-compose.yml structure, image list, model weights, config files, install script, verify script, and export script -- specific enough to build the bundle
  3. The mode parity matrix explicitly documents every feature with its online/offline status, and every divergence has a documented reason and workaround
  4. The offline update cycle specifies the signing mechanism, verification procedure, migration steps, and zero-downtime cutover sequence
**Plans**: TBD

Plans:

- [ ] 07-01: Online deployment architecture and offline Docker bundle specification
- [ ] 07-02: Mode parity matrix and offline update cycle

### Phase 8: Team Readiness Documentation

**Goal**: Gold-standard onboarding tutorials, user documentation, and role-playing scenarios exist so that new engineers, vendor data ops leads (Dana), customer success leads, and deployed engineers can perform their roles without tribal knowledge
**Depends on**: Phase 6, Phase 7
**Requirements**: ONBOARD-01, ONBOARD-02, ONBOARD-03, USERDOC-01, USERDOC-02, USERDOC-03, SCENARIO-01, SCENARIO-02
**Success Criteria** (what must be TRUE):

  1. A new engineer can follow the architecture walkthrough and explain control plane, data plane, and audit plane responsibilities without additional context
  2. The local development setup guide is executable: a developer following it step-by-step gets a running local environment with test data
  3. The first-task guide walks through adding a new document type end-to-end, producing a concrete PR-ready changeset
  4. Dana (vendor data ops lead) can follow the vendor operations guide to submit a batch, read an acceptance report, and troubleshoot common errors without engineering support
  5. CS and engineering role-play scenarios each contain 3+ realistic situations with context, expected actions, escalation criteria, and resolution steps
**Plans**: TBD

Plans:

- [ ] 08-01: Engineer onboarding tutorials (architecture walkthrough, dev setup, first task)
- [ ] 08-02: User documentation for Dana persona (operations guide, acceptance reports, troubleshooting)
- [ ] 08-03: Role-playing scenarios (customer success and deployed engineer)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
| ----- | -------------- | ------ | ---------- |
| 1. Product Definition and Tech Decisions | 2/2 | Complete | 2026-02-08 |
| 2. Tenant Isolation Architecture | 2/2 | Complete | 2026-02-09 |
| 3. Audit Stream and Document Safety | 2/2 | Complete | 2026-02-11 |
| 4. Foundation and Storage Layer Plans | 2/2 | Complete | 2026-02-11 |
| 5. Intake and Parsing Pipeline Plans | 2/2 | Complete | 2026-02-11 |
| 6. Policy, Embedding, and Serving Layer Plans | 0/3 | Not started | - |
| 7. Deployment Architecture | 0/2 | Not started | - |
| 8. Team Readiness Documentation | 0/3 | Not started | - |

---
*Created: 2026-02-08*
*Last updated: 2026-02-11 after Phase 4 completion*
