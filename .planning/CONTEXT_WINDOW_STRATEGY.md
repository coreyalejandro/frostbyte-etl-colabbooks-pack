# Context Window Strategy: Frostbyte ETL Planning Pack

**Purpose:** Ensure each phase/plan fits within one context window. Split phases when needed.

## Context Estimates (Approximate)

| Artifact | Lines | Est. Tokens (≈15/line) |
|----------|-------|------------------------|
| PRD.md | 3,110 | ~47K |
| TECH_DECISIONS.md | 411 | ~6K |
| Plan file (typical) | 300–620 | ~5–9K |
| Output doc (typical) | 500–700 | ~8–11K |
| Research file | 400–620 | ~6–9K |
| HANDOFF.md | ~100 | ~1.5K |

**Accumulated reference load by phase:**

- Phase 3: PRD + TECH + Phase 2 docs ≈ 4,500 lines (~68K tokens) — load only needed sections
- Phase 6: PRD + TECH + Phase 2 + 3 + 4 + 5 ≈ 8,000+ lines if loaded in full
- **Mitigation:** Reference by section (e.g., "PRD Section 3.4"), don't load full PRD

## Will Each Phase Fit One Context Window?

| Phase | Plans | Est. Load per Plan | Fits? | Action |
|-------|-------|--------------------|------|--------|
| 3 | 2 | Plan 300 + research 400 + refs 1K + output 600 ≈ 2.3K lines | ✅ Yes | 1 conversation for both, or 2 if preferred |
| 4 | 2 | Similar; refs grow (Phase 2 + 3) | ✅ Yes | 1–2 conversations |
| 5 | 2 | Similar | ✅ Yes | 1–2 conversations |
| 6 | **3** | Plan 400 + refs 2K + output 600 ≈ 3K lines × 3 | ⚠️ Tight | **Split: 1 plan per conversation** |
| 7 | 2 | Plan + deploy docs | ✅ Yes | 1–2 conversations |
| 8 | **3** | Plan + onboarding/docs content | ⚠️ Tight | **Split: 1 plan per conversation** |

## Recommendation

- **Phases 3, 4, 5, 7:** One phase per conversation is feasible. Optionally split 03-01/03-02 or 04-01/04-02 into separate conversations if context feels crowded.
- **Phases 6 and 8:** Already split by plan count (3 plans each). Execute **one plan per conversation** to stay within context limits.
- **Reference discipline:** When executing a plan, read only:
  - The plan file
  - Targeted PRD/TECH sections (by grep or targeted read)
  - Phase research file if the plan references it
  - Previous phase outputs only when the plan explicitly requires them

## Plan Numbering (Already Supports Splits)

- Phase 3: 03-01, 03-02
- Phase 4: 04-01, 04-02
- Phase 5: 05-01, 05-02
- Phase 6: 06-01, 06-02, 06-03
- Phase 7: 07-01, 07-02
- Phase 8: 08-01, 08-02, 08-03

No additional subdivision needed. Each NN-MM is a natural conversation boundary for Phases 6 and 8.
