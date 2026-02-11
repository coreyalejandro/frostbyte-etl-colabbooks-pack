# Phase 6: Policy, Embedding, and Serving Layer - Research

**Researched:** 2026-02-11
**Domain:** Policy engine (PII, classification, injection), embedding service (OpenRouter/Nomic), RAG serving layer
**Confidence:** HIGH (PRD, DOCUMENT_SAFETY, TECH_DECISIONS, AUDIT_ARCHITECTURE)

## Summary

Phase 6 produces three implementation plans: (1) Policy engine — PII detection (REDACT/FLAG/BLOCK), classification (rule-based + ML), injection defense (DOCUMENT_SAFETY Section 1), deterministic chunk IDs; (2) Embedding + indexing — OpenRouter (online) + Nomic (offline), 768d lock, three-store write, model version recording; (3) Serving layer — RAG retrieval flow, retrieval proof object, cite-only-from-retrieval, RETRIEVAL_EXECUTED audit.

All plans must explicitly handle online vs offline mode differences (embedding endpoint, model source).

## Requirements Traceability

| Requirement | Phase 6 Plan | Content |
|-------------|--------------|---------|
| IMPL-05 | 06-01 | Policy engine: PII, classification, injection, chunking |
| IMPL-06 | 06-02 | Embedding and indexing (OpenRouter online, Nomic offline) |
| IMPL-07 | 06-03 | Serving layer (RAG API, retrieval proofs) |

## Key References

- **PRD Section 2.3** — Policy gates (PII, classification, injection), policy-enriched chunk schema
- **PRD Section 2.4** — Embedding, three-store write, 768d lock, index metadata
- **PRD Section 2.5** — Serving flow, retrieval proof, cite-only-from-retrieval
- **DOCUMENT_SAFETY** — Injection patterns, heuristic scorer, decision tree (Section 1)
- **TECH_DECISIONS** — OpenRouter text-embedding-3-small (768d), Nomic embed-text v1.5 (768d native)
- **AUDIT_ARCHITECTURE** — POLICY_GATE_*, DOCUMENT_EMBEDDED, INDEX_WRITTEN, RETRIEVAL_EXECUTED
