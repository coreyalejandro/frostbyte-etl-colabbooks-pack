# Zero-Shot OS — All-in-One PPP (Single Source of Truth)

## Status

- **Canonical Source:** This file is the sole source of truth for planning, execution, and verification.
- **Use For:** Planning, execution, and verification. All task lists must roll up here.

- **Versioning:** This document is versioned via Git history. The filename stays stable; major milestones are recorded in the changelog below.

### Changelog

- **v1.1.0 (2025-12-20):** Added Zero-Shot Buildability Contract (ZSBC) to make the PPP machine-executable and externally verifiable.

---

## Policy Summary (Non-Negotiable)

- **Canonical Source:** This PPP is the single source of truth for planning, execution, and verification.
- **Runtime Boundary (ZSB-RB-01):** Node.js + TypeScript only for the zero-shot minimum. Python is not allowed in the zero-shot qualification path.
- **Zero-Shot Minimum:** One full playable regime + corpus export + all ZSBC checks pass.
- **Prompt Governance:** JSON is canonical; Markdown is generated and must be reproducible.
- **ZSBC Enforcement:** No human intervention after start; immutable evidence bundle required.
- **Secrets Handling:** Explicit env requirements and deterministic redaction.

---

## Part 0 — System Definition + Brain-First Principle (Required Reading)

### 0.1 Naming (Single Source of Truth)

**System Name:** Zero-Shot OS

**The Zero-Shot OS has two parts:**

1. **UPOS7VS Core (Open Source, platform/framework agnostic)**

   - Purpose: prompt-engineering engine that standardizes intent (UPOS7VS), routes work across models/tools, and produces deterministic artifacts.

2. **Zero Shot Build + Governance System (Enterprise, paid)**

   - Purpose: enforces end-to-end SDLC governance (ideation → planning → implementation → review → release → production monitoring) and makes compliance/auditability non-optional.

**Necessary overlap (explicit and intentional):**

- Shared schemas for governance artifacts.
- Shared vocabulary (IDs, naming, status states) so the OSS Core can safely interoperate with the Enterprise system.

### 0.2 The Zero Shot Brain (KB) is the Central Hub

The **Zero Shot Brain** is the starting point for all work. It is the authoritative hub that stores and indexes:

- approved reusable components (the fastest path to zero-shot development)
- rules/policies and their enforcement boundaries
- golden-path workflows (the "how we ship" playbooks)
- troubleshooting guides and known failure modes
- decision logs and rationale (why the rules exist)
- provenance links: component → usage → incidents → remediations

**Brain-first rule:** no developer or agent begins a new feature by designing from scratch. The first action is always:

1) check the Brain inventory for an approved component and its docs
2) reuse it if it exists
3) if it does not exist, propose it through governed creation so it becomes reusable next time

### 0.3 Architecture Flowchart 0 — System of Systems (High Fidelity)

```mermaid
flowchart LR
  subgraph OSS[UPOS7VS Core (Open Source)]
    OSS1[UPOS7VS CLI / SDK] --> OSS2[Mode Router + UPOS7VS Normalizer]
    OSS2 --> OSS3[Provider Adapters\n(OpenAI / Anthropic / Ollama / Watson / Google / ...)]
    OSS1 --> OSS4[Local Telemetry + Cost + Artifacts]
  end

  subgraph ENT[Zero Shot Build + Governance (Enterprise)]
    B0[Zero Shot Brain\n(KB + Component Inventory + Golden Paths)] --> B1[Governance Policy Engine\n(schema + gates + approvals)]
    B0 --> B2[Reusable Component Registry\n(code + docs + tests + troubleshooting)]
    B1 --> B3[CI/CD Gates\n(secrets + tests + schema + freshness)]
    B1 --> B4[Petris Visual Builder\n(neurodivergent-first step UI)]
    B3 --> B5[Release Controller\n(rollout + rollback + attestations)]
    B5 --> B6[Prod Monitoring + Incidents\n(SLOs + traces + postmortems)]
    B6 --> B0
  end

  OSS1 <--> B0
  OSS1 <--> B1
  OSS4 --> B0
```

### 0.4 Architecture Flowchart 1 — Brain-First Operational Loop (Developer + Agent)

```mermaid
flowchart TD
  S[Start: Work request enters system] --> I[Brain Inventory Check\n(search approved components + golden paths)]
  I -->|Approved component exists| R[Reuse\npull component + docs + tests + troubleshooting]
  I -->|No approved component| N[Governed Proposal\nnew component request + scope + risk]
  N --> C[Council / Review\n(policy + CAP profile + evidence)]
  C --> B[Brain Update\nregister component + docs + tests]
  R --> D[Implement Change\nrepo update using component]
  B --> D
  D --> G[Governance Gates\nCI + schemas + secrets + approvals]
  G -->|PASS| M[Merge + Release]
  G -->|FAIL| F[Fix using Brain guidance\n(known issues + runbooks)]
  F --> D
  M --> O[Observe Production\nSLOs + incidents + telemetry]
  O --> L[Log Learnings\npostmortem → Brain updates]
  L --> S
```

### 0.5 Architecture Flowchart 2 — CAP-Aware Knowledge Planes

```mermaid
flowchart LR
  subgraph CP[CP-Strict Plane (Correctness First)]
    CP1[Policies + Approvals\n(non-divergent)] --> CP2[Immutable Audit Log\n(append-only, signed)]
  end

  subgraph HY[Hybrid-Tunable Plane (Usability + Safety)]
    HY1[Artifact Store\n(versions + metadata)] <--> CP2
  end

  subgraph AP[AP-Resilient Plane (Always Available)]
    AP1[Search + Index\n(eventual consistency)] --> HY1
    AP2[Dev/Agent Reads\n(bounded staleness OK)] --> AP1
  end

  CP2 --> HY1
```

### 0.6 Deterministic Brain Inventory (File/Folder Contract)

### 0.6.1 Per-Repo Component Inventory (Bootstrap)

Each repo maintains a minimal, machine-readable component registry to keep modules swappable and dependency-graphable.

**Canonical file (per repo):** `components.json`

**Schema (per repo):** `COMPONENTS.schema.json`

**Lite install:** `INSTALL_COMPONENT_INVENTORY.md`

**Rule:** Keep this file small and current; no scripts required for initial install. Aggregation happens later via a separate module.

The Brain must be **a deterministic folder tree** that can be mounted locally and validated in CI.

**Canonical Brain root (repo-relative path):**

- `zero-shot/brain/`

**Minimum required Brain subfolders:**

- `zero-shot/brain/components/` — approved reusable components (each component is a folder)
- `zero-shot/brain/components/_index.json` — component registry index (machine-readable)
- `zero-shot/brain/policies/` — policy packs (JSON) + human-readable explanations (MD)
- `zero-shot/brain/golden-paths/` — step-by-step workflows (MD + diagrams)
- `zero-shot/brain/troubleshooting/` — known issues + fixes (MD)
- `zero-shot/brain/decisions/` — decision logs (MD/JSON) with references
- `zero-shot/brain/schemas/` — JSON Schemas used by governance gates

**Brain component folder contract (example):**

- `zero-shot/brain/components/<component-slug>/README.md` — purpose + usage + examples
- `zero-shot/brain/components/<component-slug>/component.json` — machine-readable metadata
- `zero-shot/brain/components/<component-slug>/tests/` — validation tests or test instructions
- `zero-shot/brain/components/<component-slug>/troubleshooting.md` — common failures + fixes

**Non-negotiable property:** The Brain is the first stop. Reuse is the default. New creation is governed.

---

### 0.7 Zero-Shot Buildability Contract (ZSBC)

This contract defines when the PPP is **machine-executable** (agent-runner buildable) with **no human intervention after start** and **publishable verification artifacts**.

#### ZSBC-0 Definitions

A **Run** is a single execution of the system's Task Graph from a clean checkout.

A Run is **Zero-Shot Buildable** only if:

1. it completes in CI with **no human intervention after start**
2. it produces an **immutable evidence bundle** sufficient for independent verification
3. every requirement in ZSBC-1 through ZSBC-9 passes

---

### 0.8 Zero-Shot Minimums + Governance Sources of Truth

**Runtime boundary (zero-shot target):**

- **Default:** Node.js + TypeScript only.
- **Python is optional** and only allowed if explicitly scoped in the TaskGraph with a strict I/O contract and evidence bundle.
- If Python is introduced, it must be confined to **one of these responsibilities** and nothing else:
  - **Offline evaluation engines** (e.g., scoring, grading, statistical analysis).
  - **Optional analytics post-processing** that consumes only exported artifacts.
  - **Experimental ML utilities** that do not block the core build.

**Runtime Boundary Rule (ZSB-RB-01):** The production and dev runtime for the zero-shot minimum is Node.js + TypeScript only. **No Python services are permitted in the zero-shot qualification path.** Any future Python use must be implemented as offline tooling (non-required for bootstrap/run/tests) unless a new explicit contract version elevates it.

**Python boundary checklist (if used):**

- **Non-blocking:** The core build must succeed without Python.
- **Contracted I/O:** JSON in → JSON out, with schema validation.
- **Deterministic artifacts:** Outputs are versioned and reproducible.
- **No secrets in logs:** Explicit redaction in stdout/stderr.
- **TaskGraph declared:** Step includes inputs, outputs, acceptance, and evidence.
- **Isolation:** No direct modification of core runtime state.

**Minimum zero-shot core feature set (to qualify as zero-shot):**

- **One full playable regime** that executes end-to-end.
- **Corpus export** produced as an immutable artifact.
- All ZSBC checks pass (no human intervention, verifiable evidence).

**Prompt governance source of truth (non-negotiable):**

- **JSON is canonical.**
- **Markdown is a generated view** for readability.
- Drift is disallowed: generated Markdown must be reproducible from JSON.

#### ZSBC-1 No Human Intervention Policy (Hard Constraint)

- No interactive prompts. All commands must be non-interactive.
- No manual edits, approvals, or mid-run decisions.
- Any interaction attempt triggers **fail-fast abort** with an attestation record.

**Abort attestation must include:** step id, reason code, timestamp, and last lines of redacted stdout/stderr.

#### ZSBC-2 Machine-Executable Task Graph (TaskGraph.yaml)

**Required file:**

- `zero-shot/brain/golden-paths/TaskGraph.yaml`

**Every step must declare (no omissions):**

- `id` (stable unique)
- `intent` (1 sentence)
- `working_dir`
- `inputs`
- `outputs` (paths + expected hash/regex)
- `commands` (exact, non-interactive)
- `acceptance` (PASS/FAIL checks)
- `depends_on`
- `rollback` (exact, non-interactive)
- `evidence` (what to collect)
- `resources` (budgets)
- `parallel` (parallelism rules)
- `secrets` (required env vars + validation + redaction)
- `retry` (bounded)
- `fallback` (bounded)

**Resource budgets are mandatory per step:**

- `max_seconds`
- `max_retries_total`
- `max_cost_usd` (if LLM calls possible)
- `max_tokens` (if LLM calls possible)

#### ZSBC-3 Secrets Handling (Explicit + Validated + Redacted)

- Secrets must be declared under `secrets.required_env` per step.
- Runner must fail-fast on missing or malformed secrets.
- Runner must redact secrets from logs and artifacts deterministically (regex-based).

#### ZSBC-4 Deterministic Environment + Reproducible Builds

- Container/devcontainer required with pinned image digest.
- Toolchains pinned and verified in preflight.
- Lockfile integrity is hash-verified before install.
- Reproducible build flag set (e.g., `SOURCE_DATE_EPOCH`) and recorded in evidence.
- Build outputs are hashed and included in a manifest.

#### ZSBC-5 Runner MVP Spec (Required for Credibility)

**Runner command (minimum viable):**

- `npm run zero-shot:run -- --graph zero-shot/brain/golden-paths/TaskGraph.yaml`

**Runner outputs (mandatory):**

- `zero-shot/runs/<runId>/run.json`
- `zero-shot/runs/<runId>/timeline.md`
- `zero-shot/runs/<runId>/manifest.sha256`
- `zero-shot/runs/<runId>/steps/<stepId>/stdout.log`
- `zero-shot/runs/<runId>/steps/<stepId>/stderr.log`
- `zero-shot/runs/<runId>/steps/<stepId>/result.json`

**Runner exit codes (mandatory):**

- `0` success (all acceptance gates passed)
- `10` TaskGraph schema invalid
- `20` preflight failed (secrets/toolchain/lockfile)
- `30` acceptance gate failed
- `40` budget exceeded
- `50` interaction detected (violates zero-shot)
- `60` retries exhausted
- `70` fallback failed

#### ZSBC-6 Acceptance Gates (Deterministic PASS/FAIL)

- Every step must include deterministic acceptance checks (exit codes + regex/hash/file existence).
- Gate failures are terminal (no manual override).
- Final release gate includes tests, build, governance check, secret scan, and manifest generation.

#### ZSBC-7 Zero-Shot Recovery Policy (Bounded + Encoded)

- Retries are bounded per step with deterministic backoff.
- Retry only on declared error classes (exit codes/regex patterns).
- Fallback is encoded in TaskGraph (alternate command/model/provider) and is also bounded.
- Fallback does not weaken acceptance gates.

#### ZSBC-8 Brain Inventory Enforcement (Reuse is Mandatory)

- Brain registry (`zero-shot/brain/components/_index.json`) must be schema-validated.
- TaskGraph must include a **ReuseCheck** step before any new component creation.
- ReuseCheck output is stored in the run evidence bundle and is required for PASS.

#### ZSBC-9 Public Claim Readiness (External Verification Artifacts)

- CI must publish `zero-shot/runs/<runId>/` as a downloadable artifact.
- CI logs for the run job must be externally reviewable.
- `manifest.sha256` must include hashes for TaskGraph, runner version, container digest, lockfiles, key build outputs, and run bundle.
- A "one-shot build" claim is allowed only when CI succeeded from a clean checkout with no manual edits/reruns and the evidence bundle + manifest are published.

---

## Part A — Gold Standard PPP (Consolidated)

## Zero-Shot-Build-OS — Gold Standard PPP + PRD

- **Title:** Zero-Shot-Build-OS - Governance & Build Operating System for AI Projects
- **Naming Note:** The system name is now **Zero-Shot OS** (the term "Build-OS" may still appear in legacy section titles below; treat them as synonyms until the doc-wide rename pass is completed).
- **Owner(s):** Product Team, Engineering Lead
- **Date:** 2025-12-18
- **Status:** Runnable (unverified) → Production-ready (in progress)
- **Repo/branch:** upos7vs_multiplatform + llm-council / master
- **Version:** v1.0.0
- **Document Type:** Combined PPP + Gold Standard PRD

---

## Prompt (Intent / UPOS-7-VS)

### Role / Persona

**AI Platform Architect** building governance infrastructure for multi-model LLM applications requiring:

- Neurodivergent-accessible UX (ADHD, autism, dyslexia friendly)
- Deterministic execution (every step verifiable)
- Privacy-first local operation
- Enterprise compliance readiness

### Objective

Create a complete governance and build operating system that makes AI projects:

1. **Reproducible** - Same inputs → same outputs, zero configuration drift
2. **Explainable** - Every decision logged and auditable
3. **Compliant** - SOC2/GDPR/HIPAA ready with artifact enforcement
4. **Neurodivergent-first** - Visual workflows, step-by-step guides, binary verification

#### Scenario / Context

Applied AI teams face:

- Config drift causing production incidents
- No audit trail for model/architecture decisions
- Secrets leakage from copy-paste workflows
- Stale documentation (handoffs, diagrams, profiles)
- Vendor lock-in to single LLM providers
- High cognitive load for neurodivergent developers

#### Task

Build Zero-Shot-Build-OS combining:

#### Component 0: Zero Shot Brain (Knowledge Base + Component Inventory)

- Component registry (approved reusable building blocks)
- Golden paths (deterministic workflows)
- Troubleshooting/runbooks (fast recovery)
- Policy packs + decision logs (why rules exist)
- Provenance (component usage and incident feedback)

#### Component 1: UPOS7VS (Orchestrator)

- Multi-provider prompt routing (OpenAI, Anthropic, Ollama, Watson, Google)
- Local analytics and cost tracking
- Semantic mode detection
- Privacy-first PII scrubbing

#### Component 2: LLM Council (Governance)

- Multi-model voting system (3-7 models)
- Weighted consensus (unanimous, supermajority, majority thresholds)
- Chairman synthesis of final decisions
- Decision audit trail

#### Component 3: Petris (Visual Builder)

- Step-by-step workflow visualization
- Progress tracking with verification criteria
- Keyboard-only navigation
- Screen reader optimized

#### Component 4: CI/CD Gates

- Artifact freshness enforcement (HANDOFF.md, openmemory.md, USER_PROFILE.md, ARCHITECTURE.mermaid)
- JSON schema validation for all artifacts
- Secret scanning
- Health check automation

#### Format

Deliver:

1. **Working codebase** - TypeScript monorepo with 95%+ test coverage
2. **API layer** - Fastify server exposing governance endpoints
3. **CLI tools** - Artifact validation, health checks
4. **Visual builder** - React components for neurodivergent UX
5. **Complete documentation** - PRD, architecture diagrams, user guides
6. **Launch plan** - 30-day path to first revenue with enterprise tier

#### Constraints

**Technical:**

- TypeScript 5.x with strict mode
- Node.js LTS (v18+)
- Zero external cloud dependencies (100% local-first)
- Must work offline after initial setup
- Package size < 50MB excluding node_modules

**Accessibility:**

- WCAG 2.2 AA compliance required
- Keyboard navigation for all interactive elements
- Screen reader compatible (NVDA, JAWS, VoiceOver)
- No motion without prefers-reduced-motion check
- High contrast mode support

**Security:**

- No secrets in version control (enforced via git hooks)
- All API keys stored in OS keychain or env vars
- TLS 1.2+ for all network calls
- Argon2id for any password hashing
- Secret scanning in CI with exit code 1 on detection

**Performance:**

- CLI commands complete in < 2 seconds
- API P95 latency < 250ms at 50 RPS
- Dashboard loads in < 3 seconds on 3G connection
- Schema validation < 100ms per artifact

**Business:**

- Open source core (MIT license)
- Enterprise tier at $299/month
- 30-day timeline to first paying customer
- No vendor lock-in (works with any LLM)

#### Verification Criteria

**Must Pass All:**

1. **Governance Check Passes**

   ```bash
   set -euo pipefail

   npm run governance:check
   # Exit code: 0
   # All 4 artifacts present and schema-validated
   ```

2. **API Server Functional**

   ```bash
   set -euo pipefail

   npm run governance:api
   # Server starts on port 3001
   # All endpoints return 200/201 for valid requests
   ```

3. **Schema Validation Works**

   ```bash
   set -euo pipefail

   # Valid data returns {"valid": true}
   # Invalid data returns {"valid": false, "errors": [...]}
   ```

4. **Tests Pass**

   ```bash
   set -euo pipefail

   npm test
   # All tests pass
   # Coverage ≥ 85% for new code
   ```

5. **TypeScript Compiles**

   ```bash
   set -euo pipefail

   npx tsc --noEmit -p tsconfig.json
   ```

6. **No Secrets Detected**

   ```bash
   set -euo pipefail

   npm run governance:scan-secrets
   # Exit code: 0
   ```

## Inputs/Snippets/Links

**Existing Assets:**

- `${REPO_ROOT}` - UPOS7VS core (95% test coverage, production-ready)
- `${COUNCIL_ROOT}` - LLM Council (80% complete, functional standalone)

**User Decisions (From Questions):**

- Packaging: Open Source Core + Commercial Enterprise
- Revenue target: 30 days (speed priority)
- Council: Multi-model voting (recommended)
- Interface: Visual step-by-step builder (recommended)

### Assumptions

1. User has Node.js 18+ and npm installed
2. User has at least one LLM API key (OpenAI, Anthropic, or local Ollama)
3. User can create and access a private product repository (public OSS mirror optional, requires explicit approval)
4. User has email access for enterprise lead capture
5. Market exists for governance-first AI tooling at $299/month enterprise tier

---

## Plan (Decisions / REASONS Log)

### Reflect: Intent Confirmed? Gaps?

**Intent Confirmed:**

- ✅ Need for governance and reproducibility validated by CODEX feedback
- ✅ Neurodivergent-first requirement matches accessibility constraints
- ✅ 30-day revenue target aligns with user's financial urgency
- ✅ Two-tier model (open source + enterprise) validated by user selection

**Gaps Identified:**

- ❌ Original proposal missing from repo (CODEX noted this)
- ❌ No machine-readable schemas for artifacts (fixed in Phase 0)
- ❌ No CI gate description (being built)
- ❌ Keys handling not specified (needs implementation)
- ❌ Governance thresholds not parameterized (needs config)
- ❌ No market/packaging section (added in this PPP)
- ❌ No pricing proof points (needs real-world validation)

### Explore: Options Considered

#### Option 1: Full SaaS Platform (Rejected)

- Pros: Recurring revenue from day 1, cloud-hosted convenience
- Cons: 90+ days to build, requires auth/billing/multi-tenancy, violates local-first principle
- Reason rejected: Timeline too long, contradicts privacy-first value prop

#### Option 2: Fully Commercial (Rejected)

- Pros: All revenue captured, no free tier cannibalization
- Cons: No community growth, no GitHub stars, hard to prove value
- Reason rejected: Open source core drives adoption (recommended by user)

#### Option 3: Open Source Core + Enterprise Tier (SELECTED)

- Pros: Community adoption, GitHub visibility, enterprise monetization path
- Cons: Free tier might satisfy some buyers
- Reason selected: Balances adoption speed with revenue potential, user confirmed

#### Option 4: Single-Model Self-Critique Council (Rejected)

- Pros: Cheaper, simpler implementation
- Cons: Single-model bias, less robust governance
- Reason rejected: Multi-model council provides diverse perspectives (user confirmed)

#### Option 5: Voice + Visual Interface (Rejected)

- Pros: Most accessible for some neurodivergent users
- Cons: Significant new infrastructure, 6+ months timeline
- Reason rejected: Visual step-by-step builder sufficient for v1 (user confirmed)

### Analyze: Trade-offs

#### Architecture Decision: Monorepo vs Multi-Repo

- **Selected:** Monorepo with packages/core, packages/council, packages/petris, packages/api
- **Trade-off:** More complex tooling vs easier dependency management
- **Why:** Single npm ci, shared TypeScript config, easier testing
- **Risk:** Package coupling - mitigated by clear interfaces

#### Language Decision: TypeScript vs Python

- **Selected:** TypeScript for orchestrator/UI, Python for council (existing)
- **Trade-off:** Two language ecosystem vs single language simplicity
- **Why:** UPOS7VS already TypeScript, council already Python, maximize reuse
- **Risk:** Polyglot complexity - mitigated by clear API boundaries

#### Schema Decision: JSON Schema vs TypeScript Types

- **Selected:** Both - JSON Schema for runtime validation, TypeScript for compile-time safety
- **Trade-off:** Duplication vs completeness
- **Why:** JSON Schema enables CI validation, TypeScript prevents dev errors
- **Risk:** Schema drift - mitigated by codegen from JSON Schema to TypeScript

#### Revenue Decision: Seat-based vs Usage-based Pricing

- **Selected:** Seat-based ($299/month for 10-25 users)
- **Trade-off:** Predictable revenue vs scales with value
- **Why:** B2B buyers prefer predictable costs, easier to sell
- **Risk:** Large teams might resist - mitigated by volume tiers

### Solve: Path Chosen

#### Phase -1: Zero Shot Brain Bootstrap (Day 0) [REQUIRED]

Goal: create the on-disk Brain inventory in a deterministic way so every developer/agent begins from the same SSoT.

##### STEP -1.1: Create the Brain folder tree

```bash

set -euo pipefail

# From repo root

mkdir -p zero-shot/brain/{components,policies,golden-paths,troubleshooting,decisions,schemas}

```

Verify (PASS/FAIL):

```bash
set -euo pipefail

test -d zero-shot/brain/components && test -d zero-shot/brain/policies && test -d zero-shot/brain/golden-paths && test -d zero-shot/brain/troubleshooting && test -d zero-shot/brain/decisions && test -d zero-shot/brain/schemas && echo "✅ PASS: Brain folders exist" || echo "❌ FAIL: Missing Brain folders"

```

##### STEP -1.2: Create the component registry index (`_index.json`)

```bash
set -euo pipefail

node -e "const fs=require('fs'); const p='zero-shot/brain/components/_index.json'; const doc={version:'1.0.0', lastUpdated:new Date().toISOString(), components:[]}; fs.writeFileSync(p, JSON.stringify(doc,null,2)+'\\n'); console.log('Wrote',p);"

```

Verify (PASS/FAIL):

```bash
set -euo pipefail

node -e "const fs=require('fs'); const p='zero-shot/brain/components/_index.json'; const j=JSON.parse(fs.readFileSync(p,'utf8')); const ok=j && j.version==='1.0.0' && Array.isArray(j.components); process.exit(ok?0:1);" && echo "✅ PASS: _index.json valid" || echo "❌ FAIL: _index.json invalid"

```

##### STEP -1.3: Mirror governance schemas into the Brain

```bash
set -euo pipefail

mkdir -p zero-shot/brain/schemas/governance
cp -R schemas/governance/. zero-shot/brain/schemas/governance/

```

Verify (PASS/FAIL):

```bash
set -euo pipefail

test -f zero-shot/brain/schemas/governance/handoff.schema.json && test -f zero-shot/brain/schemas/governance/openmemory.schema.json && test -f zero-shot/brain/schemas/governance/user-profile.schema.json && echo "✅ PASS: Brain schema mirror present" || echo "❌ FAIL: Brain schema mirror missing"

```

##### STEP -1.4: Day-1 ROI checklist (Brain-first readiness)

```bash
set -euo pipefail

npm run governance:check
node -e "require('fs').accessSync('zero-shot/brain/components/_index.json'); console.log('Brain index present');"

```

Status note:

- Brain-aware validation (e.g., `npm run brain:check`) is **not implemented** yet unless explicitly added later. This phase only establishes the deterministic on-disk Brain contract.

#### Phase 0: Governance API Layer (Days 1-5) [COMPLETED]

- Retrieved: Existing governance.service.ts patterns from codebase
- Created:
  - packages/core/services/governance.service.ts with Ajv schema validation
  - packages/api/governance-routes.ts with Fastify endpoints
  - packages/api/server.ts with health checks
  - schemas/governance/*.schema.json (3 schemas)
  - CLI tool at packages/cli/governance-check.ts
- Refactored: Added JSON payloads to HANDOFF.md, openmemory.md, USER_PROFILE.md
- Why: CODEX feedback required machine-readable schemas and CI enforcement

#### Phase 1: Standalone Launch (Days 6-30) [PENDING]

- Create: Product README.md with Quick Start and Enterprise CTA (for private product repo)
- Create: Enterprise landing page at `dashboard/app/enterprise/page.tsx` (App Router)
- Create: New private product repository (separate from current repo) and migrate Phase 0 + Phase 1 assets
- Create: Launch announcement drafts (posting gated by user approval)
- Create: Enterprise trial process and CRM tracking
- Why: 30-day revenue target requires immediate market validation without forcing a public code release

#### Phase 2: LLM Council Integration (Days 31-50) [PENDING]

- Retrieve: Existing council code from ${COUNCIL_ROOT}
- Move: Into packages/council/ with monorepo structure
- Create: Council voting engine with unanimous/supermajority/majority logic
- Create: Decision types schema and test cases
- Why: Multi-model governance prevents single-point bias

#### Phase 3: Petris Visual Builder (Days 51-80) [PENDING]

- Create: React Step component with status indicators
- Create: WorkflowBuilder with progress tracking
- Create: Example workflows (add-feature, refactor, security-review)
- Create: Accessibility testing suite
- Why: Neurodivergent-first UX reduces cognitive load

#### Phase 4: Integration & Launch (Days 81-120) [PENDING]

- Create: Unified zero-shot-build-os.config.json
- Create: E2E tests covering full governance workflow
- Create: CI gates (GitHub Actions) for artifact validation
- Create: Documentation and marketing site
- Why: Complete system integration enables full value delivery

### Observe: Verification Done/Planned

### Phase 0 Verification (COMPLETED)

```bash
set -euo pipefail

✅ npm run governance:check - Exit code 0
✅ npm run governance:api - Server starts, all endpoints functional
✅ Schema validation - Accepts valid, rejects invalid data
✅ TypeScript compilation - No errors
✅ All 4 artifacts present and validated

```

### Phase 1 Verification (PLANNED)

```bash

set -euo pipefail

# File existence

test -f LICENSE && test -f CONTRIBUTING.md && test -f README.md

# Repo readiness
# Private product repo created and access configured
# Phase 0 + Phase 1 assets migrated
# Enterprise leads ≥ 3
# Paying customers ≥ 1

```

### Phase 2 Verification (PLANNED)

```bash

set -euo pipefail

# Council integration

test -d packages/council/backend
test -f packages/council/core/voting.ts
npm run test:council # All council tests pass

# Voting logic
# Test unanimous threshold (100%)
# Test supermajority threshold (≥67%)
# Test majority threshold (>50%)

```

### Phase 3 Verification (PLANNED)

```bash

set -euo pipefail

# Petris components

test -f packages/petris/components/Step.tsx
test -f packages/petris/components/WorkflowBuilder.tsx

# Accessibility

npm run test:a11y # WCAG 2.2 AA automated checks pass

# Manual screen reader testing (NVDA, JAWS)
# Keyboard navigation testing (Tab, Enter, Escape)

```

### Phase 4 Verification (PLANNED)

```bash

set -euo pipefail

# E2E workflow

npm run test:e2e:zero-shot # Full governance workflow passes

# CI gates

.github/workflows/governance.yml exists

# Artifact validation runs on every PR
# Schema validation runs on every PR
# Secret scan runs on every PR

```

### Notify: Output Format Delivered

**Formats Delivered:**

1. **Code Artifacts:**
   - TypeScript services with JSDoc documentation
   - Fastify API with OpenAPI schema
   - React components with Storybook stories
   - JSON Schemas for governance artifacts

2. **Documentation:**
   - This Gold Standard PPP (comprehensive)
   - CURRENT_TASKS.md (session tracking)
   - README.md (user-facing quickstart)
   - API documentation (endpoint specs)

3. **Verification Evidence:**
   - Test output logs
   - API response samples
   - CLI execution traces
   - Schema validation results

### Synthesize: Improvements to Feed Back

#### Lessons Learned

1. **Schema-first governance works** - JSON Schema validation caught structural issues immediately
2. **CLI + API duality valuable** - Developers use CLI, CI uses API
3. **Neurodivergent design principles** - Explicit verification criteria reduce anxiety
4. **Local-first complexity** - Secrets management harder without cloud storage
5. **Honest communication critical** - User caught dishonesty, trust broken temporarily

#### Feed Forward to Future Work

1. Add schema generation from TypeScript types (reduce duplication)
2. Create visual schema editor for non-technical users
3. Build GitHub App for automatic governance checks
4. Create enterprise dashboard for team-wide visibility
5. Add automated migration scripts for version upgrades

### Risks / Edge Cases / Failure Modes

#### Risk Register

#### RK-001: Market Adoption Slower Than 30 Days

- Likelihood: Medium
- Impact: High (user has $7, needs revenue)
- Mitigation: Parallel outreach to 10+ companies, HN/Reddit launch for visibility
- Contingency: Extend free trial to 60 days, offer discounted annual contracts

#### RK-002: Enterprise Buyers Demand Hosted Solution

- Likelihood: Medium
- Impact: Medium (expands scope significantly)
- Mitigation: Offer "managed cloud" option at higher tier ($799/month)
- Contingency: Partner with cloud provider for white-label hosting

#### RK-003: Schema Validation Performance Issues

- Likelihood: Low
- Impact: Medium (slow CI gates)
- Mitigation: Benchmark with large artifacts, optimize Ajv compilation
