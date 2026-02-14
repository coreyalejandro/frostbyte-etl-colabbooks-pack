# Reproduce the Zero-Shot PRD Plan (Phase 1)

This document describes how to reproduce the planning process that produced `docs/product/PRD.md` and `docs/reference/TECH_DECISIONS.md`. Use this to re-run the planning, fork it for a new project, or hand off to an AI agent.

---

## What Was Produced

| Artifact | Purpose |
|----------|---------|
| `docs/product/PRD.md` | Product Requirements Document — pipeline lifecycle, personas, tenant state machine, API contracts, monitoring |
| `docs/reference/TECH_DECISIONS.md` | Technology choices — 35 components, version pins, online/offline manifests |

---

## Source Materials (Required Inputs)

Before running the plans, ensure these exist. They are the context the plans synthesize from.

| File | Purpose |
|------|---------|
| `docs/product/ETL_PIPELINE_PROPOSAL.md` | Original proposal — phases, tools, alternatives |
| `docs/product/CUSTOMER_JOURNEY_MAP.md` | Dana persona, pain points P1–P5 |
| `docs/security/THREAT_MODEL_SAFETY.md` | Security posture, injection defenses |
| `diagrams/architecture.mmd` | Mermaid architecture diagram |
| `diagrams/tenancy.mmd` | Mermaid tenancy diagram |
| `.planning/research/ARCHITECTURE.md` | Three-plane architecture, control/data/audit |
| `.planning/research/FEATURES.md` | Feature set, anti-features AF-1 to AF-6 |
| `.planning/research/PITFALLS.md` | Known pitfalls, dimension mismatch, etc. |
| `.planning/phases/01-product-definition-and-tech-decisions/01-RESEARCH.md` | Phase 1 research — stack, patterns |

---

## Plan Files (Execution Instructions)

| Plan | Output | Instructions |
|------|--------|--------------|
| `01-01-PLAN.md` | `docs/product/PRD.md` | Execute tasks 1–N in order. Each task specifies section structure, content, diagrams. |
| `01-02-PLAN.md` | `docs/reference/TECH_DECISIONS.md` | Execute tasks. Component table, version pins, manifests. |

---

## How to Reproduce (AI Agent)

1. **Load context:** Read all source materials listed above.
2. **Execute 01-01-PLAN.md:**
   - Follow the `<tasks>` section.
   - Create `docs/product/PRD.md` with Sections 1–5 per the plan.
   - Include Mermaid diagrams, state transition table, API schemas.
3. **Execute 01-02-PLAN.md:**
   - Follow the `<tasks>` section.
   - Create `docs/reference/TECH_DECISIONS.md` with component decisions, manifests, compatibility matrix.
4. **Verify:** Run checks in each plan’s `<verification>` block.

---

## How to Reproduce (Human)

1. Open `01-01-PLAN.md` and `01-02-PLAN.md`.
2. Use the plan as a checklist: each task has an `<action>` block with concrete steps.
3. Write the documents section by section, synthesizing from the source materials.
4. Run the verification commands in each plan.

---

## Workflow Reference

The plans reference the get-shit-done workflow:

- `@/Users/coreyalejandro/.claude/get-shit-done/workflows/execute-plan.md`
- `@/Users/coreyalejandro/.claude/get-shit-done/templates/summary.md`

If those paths do not exist, treat the plan as a deterministic specification: execute each task’s `<action>` literally.

---

## After Reproducing

Create summaries per the plan `<output>` section:

- `.planning/phases/01-product-definition-and-tech-decisions/01-01-SUMMARY.md`
- `.planning/phases/01-product-definition-and-tech-decisions/01-02-SUMMARY.md`

Then run Phase 1 verification (see `01-VERIFICATION.md` if present).
