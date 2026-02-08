# Frostbyte Multi-Tenant ETL Pipeline — Zero-Shot Implementation Pack

## What This Is

A comprehensive, deterministic planning package for Frostbyte's multi-tenant ETL pipeline (variant 05: Hetzner-isolated tenants). This is an audition deliverable demonstrating how Corey would approach building the pipeline end-to-end — from PRD through implementation plans, onboarding documentation, user guides, and team preparation materials. The plans are written so that any engineer or AI agent can execute them without ambiguity.

## Core Value

Every planning artifact must be so specific and deterministic that a person who has never seen the codebase could build, deploy, support, and explain the system by following the documents alone.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Zero-shot PRD covering the full multi-tenant ETL pipeline (intake, parsing, enrichment, storage, serving, audit, offline mode)
- [ ] Locked-in tech decisions for every component (no "choose between X and Y" — one answer, one rationale)
- [ ] Step-by-step implementation plans for each pipeline phase, detailed enough for blind execution
- [ ] Per-tenant isolation architecture fully specified (Hetzner provisioning, per-tenant keys, storage namespaces, network boundaries)
- [ ] Dual-mode deployment plans: online API mode + offline air-gapped Docker bundle
- [ ] Gold standard onboarding tutorials for new engineers joining the project
- [ ] Gold standard user documentation for vendor data operations leads (the "Dana" persona)
- [ ] Role-playing scenarios for customer success leads handling real support situations
- [ ] Role-playing scenarios for deployed engineers handling technical escalations
- [ ] Vendor acceptance report workflow documented end-to-end
- [ ] Immutable audit stream design with concrete schema and query patterns
- [ ] Injection defense and document-safety controls specified with implementation detail

### Out of Scope

- Writing production code — this is the planning pack, not the build
- CI/CD pipeline configuration — infrastructure automation is implementation, not planning
- Pricing or commercial terms — this is a technical deliverable
- Cross-tenant analytics or aggregation features — explicitly excluded per Frode's security posture
- Real-time streaming ingestion — batch-first pipeline per the original sketch

## Context

**Origin:** Frode (Frostbyte) described the pipeline sketch: "document in, structure out, stored in DB and vector" with Unstructured + Docling, OpenRouter embeddings, Hetzner tenant isolation, and offline Docker mode. Corey constructed five viable use-case notebooks via verbalized sampling prompts with ChatGPT. This project takes the 5th variant (multi-tenant Hetzner isolation) and builds the full planning infrastructure around it.

**Frostbyte's positioning:** Enterprise AI infrastructure for regulated industries. Data sovereignty is non-negotiable. Documents are treated as untrusted inputs. Tenant isolation is by construction, not by policy.

**Existing artifacts in this repo:**
- `docs/ETL_PIPELINE_PROPOSAL.md` — full proposal (phases, tools, alternatives)
- `docs/CUSTOMER_JOURNEY_MAP.md` — Dana persona + journey map with pain points
- `docs/THREAT_MODEL_SAFETY.md` — security posture, injection defenses, auditability
- `diagrams/*.mmd` — Mermaid diagrams (architecture, tenancy, offline bundle)
- `templates/VENDOR_ACCEPTANCE_REPORT.md` — acceptance report template
- `notebooks/05_multi_tenant_isolation_hetzner.ipynb` — the source variant being expanded

**Audience:** This planning pack serves two consumers:
1. Human engineers — Frode's team or future hires who implement the pipeline
2. AI agents — Claude, GPT, or similar tools that execute deterministic prompts

**Purpose:** Job audition. Demonstrates Corey's approach to data engineering projects: plan thoroughly, document for support from day one, prepare the team before launch.

## Constraints

- **Tech stack**: Python (ETL/ML), Hetzner Cloud API (infra), Docling + Unstructured (parsing), OpenRouter (online embeddings), Nomic embed-text (offline embeddings) — all specified by Frode
- **Sovereignty**: All data processing must respect per-tenant isolation boundaries; no cross-tenant data flows
- **Offline capability**: Pipeline must run fully air-gapped via Docker Compose with zero outbound network calls
- **Documents as threats**: Every ingestion path treats documents as untrusted inputs; injection defense is mandatory, not optional
- **Determinism**: Plans must be executable without interpretation — no "choose the best approach" language

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Expand variant 05 (multi-tenant Hetzner) | Most complex variant, demonstrates deepest competence | — Pending |
| Planning pack, not code | Audition demonstrates approach + thinking, not just coding ability | — Pending |
| Include team preparation materials | Frostbyte values enterprise readiness; support infrastructure matters as much as the system | — Pending |
| Lock in all tech choices | Deterministic plans require opinionated decisions; Frode's sketch already names the tools | — Pending |
| Role-playing scenarios for CS + engineering | Differentiator — most candidates don't think about post-launch team readiness | — Pending |

---
*Last updated: 2026-02-08 after initialization*
