# Plan 05-02 Summary: Parsing Pipeline

**Executed:** 2026-02-11
**Plan:** 05-02-PLAN.md
**Output:** docs/design/PARSING_PIPELINE_PLAN.md

## Delivered

1. **Stage 1 (Docling)** — Layout extraction (sections, tables, figures, reading_order), OCR fallback
2. **Stage 2 (Unstructured)** — Partition, chunk by_title, deterministic chunk_id
3. **Stage 3** — Canonical JSON assembly, lineage, stats, write to normalized path
4. **Canonical schema** — Pydantic-ready models (CanonicalStructuredDocument, Chunk, Section, Table, etc.)
5. **Parse failure** — DOCUMENT_PARSE_FAILED, CONTENT_DROPPED, acceptance report integration
6. **Audit events** — DOCUMENT_PARSED, DOCUMENT_PARSE_FAILED, CONTENT_DROPPED

## Lines

docs/design/PARSING_PIPELINE_PLAN.md: ~480 lines (meets min 450)
