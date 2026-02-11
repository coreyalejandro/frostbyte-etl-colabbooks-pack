# Phase 5: Intake and Parsing Pipeline - Research

**Researched:** 2026-02-11
**Domain:** Intake gateway (trust boundary), document parsing (Docling + Unstructured)
**Confidence:** HIGH (PRD, TECH_DECISIONS, DOCUMENT_SAFETY, AUDIT_ARCHITECTURE)

## Summary

Phase 5 produces two implementation plans: (1) Intake gateway — full request flow from vendor upload (auth, manifest validation, MIME/checksum/malware checks, object store write, receipts, audit events, job enqueue); (2) Parsing pipeline — Docling (layout-aware conversion) + Unstructured (partitioning/chunking), canonical JSON schema, lineage structure, parse failure reporting.

Both plans reference Phase 3 (AUDIT_ARCHITECTURE event types, DOCUMENT_SAFETY MIME/file allowlisting) and Phase 4 (FOUNDATION_LAYER_PLAN tenant config, STORAGE_LAYER_PLAN object store paths).

## Requirements Traceability

| Requirement | Phase 5 Plan | Content |
|-------------|-------------|---------|
| IMPL-03 | 05-01 | Intake gateway: auth, manifest, checksum, MIME, malware scan, receipts |
| IMPL-04 | 05-02 | Parsing pipeline: Docling + Unstructured, canonical JSON schema |

## Key References

### Intake Gateway (05-01)

- **PRD Section 2.1** — Intake flow, manifest schema, per-file checks, receipt schemas, error handling
- **PRD Section 5.4** — `POST /api/v1/ingest/{tenant_id}/batch`, `GET batch/{batch_id}`, `GET receipt/{receipt_id}` with auth, rate limits, error codes
- **DOCUMENT_SAFETY Section 3** — MIME verification (libmagic), per-tenant allowlist, intake integration order
- **TECH_DECISIONS** — python-magic (libmagic), ClamAV sidecar, python-jose (JWT), python-multipart
- **AUDIT_ARCHITECTURE Section 1.2** — BATCH_RECEIVED, DOCUMENT_INGESTED, DOCUMENT_REJECTED, DOCUMENT_QUARANTINED

### Parsing Pipeline (05-02)

- **PRD Section 2.2** — Stage 1 (layout-aware), Stage 2 (partitioning/chunking), Stage 3 (canonical JSON), outputs, error handling
- **PRD canonical JSON schema** — doc_id, sections, tables, figures, reading_order, chunks, lineage, stats
- **TECH_DECISIONS** — Docling >=2.70, Unstructured >=0.16, Pydantic >=2.10
- **AUDIT_ARCHITECTURE Section 1.2** — DOCUMENT_PARSED, DOCUMENT_PARSE_FAILED, CONTENT_DROPPED
- **TENANT_ISOLATION_STORAGE_ENCRYPTION** — Object store path `normalized/{tenant_id}/{doc_id}/structured.json`

## Intake Flow (Condensed)

1. TLS → JWT validation (extract tenant_id) → rate limit (100/min)
2. Manifest validation (parse JSON, file count match, no duplicate file_ids)
3. Per-file: MIME (libmagic vs allowlist) → size → checksum → malware (ClamAV) → write raw to `raw/{tenant_id}/{file_id}/{sha256}` → receipt → audit → enqueue parse
4. Return batch receipt (accepted, rejected, quarantined counts + detail)

## Parsing Flow (Condensed)

1. Read raw from object store; Stage 1 (Docling): layout extraction (sections, tables, figures, reading order, offsets); OCR for scanned
2. Stage 2 (Unstructured): partition, chunk by_title, deterministic chunk_id = hash(doc_id + page + start + end)
3. Stage 3: merge, write `normalized/{tenant_id}/{doc_id}/structured.json`, lineage (raw_sha256, parser versions)
4. Emit DOCUMENT_PARSED; enqueue policy check

## Sources

- docs/PRD.md (Sections 2.1, 2.2, 5.4)
- docs/TECH_DECISIONS.md (Components 3, 4, 10, 28, 29, 30, 32)
- docs/DOCUMENT_SAFETY.md (Section 3)
- docs/AUDIT_ARCHITECTURE.md (Section 1.2)
- docs/FOUNDATION_LAYER_PLAN.md
- docs/STORAGE_LAYER_PLAN.md (MinIO paths)
- .planning/research/ARCHITECTURE.md (intake/parse flow)
