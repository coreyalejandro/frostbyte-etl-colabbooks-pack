# Phase 3: Audit Stream and Document Safety - Research

**Researched:** 2026-02-11
**Domain:** Immutable audit stream architecture, document safety controls (injection defense, content boundary, file-type allowlisting)
**Confidence:** HIGH (synthesized from ARCHITECTURE.md, PITFALLS.md, THREAT_MODEL_SAFETY.md, PRD Appendix A–H, FEATURES.md)

## Summary

Phase 3 produces two architecture documents: (1) Audit stream design covering event schema, immutable storage, and auditor query patterns; (2) Document safety design covering injection defense, content boundary enforcement, and file-type allowlisting. Both documents are standalone references that every implementation plan (Phases 4–7) can cite by section.

**Primary recommendation:** Use PostgreSQL append-only tables with `INSERT`-only grants for the audit store. Implement hash chain integrity (`previous_event_id` linking) for tamper evidence. Specify injection defense as a three-tier decision tree (PASS/FLAG/QUARANTINE) with concrete regex patterns and heuristic thresholds. Enforce the envelope pattern at every pipeline stage so document content is always wrapped in trusted metadata and never interpreted as system instructions.

## Requirements Traceability

| Requirement | Phase 3 Plan | Document Section |
|-------------|--------------|------------------|
| AUDIT-01 | 03-01 | Audit event schema (fields, event types, hash chain) |
| AUDIT-02 | 03-01 | Immutable storage (append-only mechanism, tamper evidence, DDL) |
| AUDIT-03 | 03-01 | Query patterns and export (by tenant, by document, by time range) |
| SAFETY-01 | 03-02 | Injection defense (patterns, scoring, quarantine rules, decision tree) |
| SAFETY-02 | 03-02 | Content boundary enforcement (envelope pattern, stage-by-stage examples) |
| SAFETY-03 | 03-02 | File-type allowlisting (MIME verification, libmagic, per-tenant config) |

## Architecture Patterns

### Pattern 1: Append-Only Audit Storage

**What:** Audit events are written once and never modified or deleted. The storage mechanism enforces this at the database or file system level.

**When to use:** Always. Per PITFALLS.md C4, audit logging as an afterthought leads to gaps and mutability. The audit store is a core data model, not a logging layer.

**Implementation options:**

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| PostgreSQL + grants | Revoke UPDATE/DELETE on audit table from all roles | Simple, uses existing stack | Application role could still have superuser; requires strict RBAC |
| PostgreSQL trigger | `BEFORE UPDATE/DELETE` raises exception | Enforced at DB level | Triggers can be dropped by DBA |
| Write-once object store | S3 Object Lock or WORM bucket | Strongest guarantee | Adds storage tier, export complexity |
| Append-only log file | Rotate, sign, and archive | Offline-mode friendly | Query complexity, no SQL |

**Recommendation:** PostgreSQL append-only table with:

1. `REVOKE UPDATE, DELETE ON audit_events FROM ...` for application roles
2. Separate read-only role for auditors
3. `previous_event_id` hash chain for tamper evidence
4. Offline mode: same schema in SQLite, exported as signed JSON Lines

### Pattern 2: Hash Chain for Tamper Evidence

**What:** Each audit event references the preceding event's ID. The `input_hash` of event N must equal the `output_hash` of event N-1. A broken chain indicates tampering or ordering error.

**When to use:** For document provenance chains. Not required for tenant lifecycle events (which are independent).

**Chain structure:**

```
DOCUMENT_INGESTED (previous_event_id: null)
  output_hash: sha256(raw_file)
    |
    v
DOCUMENT_PARSED (previous_event_id: <ingested_id>)
  input_hash: sha256(raw_file)  -- must match above
  output_hash: sha256(canonical_json)
    |
    v
POLICY_GATE_PASSED (previous_event_id: <parsed_id>)
  ...
```

**Verification:** The provenance chain API (`GET /api/v1/audit/{tenant_id}/chain/{resource_id}`) walks the chain and reports any `input_hash != previous.output_hash` mismatches.

### Pattern 3: Injection Defense Decision Tree

**What:** Three-tier action based on heuristic score: `< 0.3` PASS, `0.3–0.7` FLAG (allow with warning), `> 0.7` QUARANTINE (do not embed).

**When to use:** Phase C (Policy Gates), Gate 3. Must run BEFORE embedding. Per ARCHITECTURE.md and PITFALLS.md C2, malicious content must never reach the vector store.

**Pattern categories (from PRD Appendix G):**

- Direct instruction override: "Ignore previous instructions", "Forget everything above"
- Role assumption: "You are now...", "Act as if..."
- Delimiter injection: "```system", "<|im_start|>system"
- Homoglyph substitution: Cyrillic/similar Unicode lookalikes
- Invisible characters: U+200B, U+200D, U+202E
- Encoding evasion: Base64, ROT13

**Heuristic factors:**

- Number and severity of pattern matches
- Unusual character distributions (high ratio of control/invisible chars)
- Instruction-like sentence structures (imperative verbs, second person)

### Pattern 4: Envelope Pattern (Content Boundary)

**What:** Document content is always wrapped in a metadata envelope. The system treats the content field as opaque data. Metadata (tenant_id, doc_id, stage, lineage) is system-controlled and trusted.

**When to use:** At every pipeline stage—intake receipt, canonical JSON, policy-enriched chunks, embedding input, retrieval proof.

**Structure:**

```json
{
  "_envelope": {
    "tenant_id": "tenant_abc",
    "doc_id": "doc_001",
    "stage": "policy_enriched",
    "lineage": { "raw_sha256": "...", "parse_version": "1.0" }
  },
  "content": "<untrusted document text — never parsed as instructions>"
}
```

**Critical rule:** Raw document text is NEVER concatenated into system prompts, tool instructions, or LLM context without explicit content-only demarcation (e.g., `[CONTENT_START]... [CONTENT_END]`).

### Pattern 5: File-Type Allowlisting

**What:** Strict MIME allowlist plus libmagic content sniffing. Extension-only checks are insufficient (polyglot files, disguised executables).

**When to use:** At intake gateway, before any parsing. Per FEATURES.md TS-1.3, MIME verification is required in addition to extension checks.

**Allowlist (from PRD Appendix C):**

- PDF, DOCX, XLSX, TXT, CSV, PNG, TIFF
- Explicit deny: .doc, .xls, .ppt(x), .html, .eml, .msg, archives, executables

**Verification sequence:**

1. Check file extension against allowlist
2. Run libmagic (or equivalent) to sniff actual content type
3. Reject if sniffed MIME != declared MIME or if sniffed MIME not on allowlist

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MIME detection | Extension-only checks | python-magic (libmagic) or filetype | Polyglot files bypass extension checks |
| Injection patterns | Ad-hoc keyword list | Curated regex set + homoglyph normalization | Coverage and maintainability |
| Audit storage | Application log files | Dedicated append-only table/stream | Log rotation loses events; mutability |
| Content boundary | Inline concatenation | Structured envelope with explicit content field | Injection via document text |

## Common Pitfalls

### Pitfall 1: Audit Events in Application Database with UPDATE Rights

**What goes wrong:** Audit events stored in the same PostgreSQL database as application data, with the application role having UPDATE/DELETE. A bug or compromise allows modification of historical events.

**How to avoid:** Separate audit schema or database, or explicitly REVOKE UPDATE/DELETE. Document the grant structure in the Phase 3 output.

### Pitfall 2: Injection Defense After Embedding

**What goes wrong:** Documents are embedded first, injection check later. Malicious chunks are already in the vector store and can influence retrieval.

**How to avoid:** Injection gate MUST be in Phase C (Policy Gates), before the embedding phase. Document this ordering constraint explicitly.

### Pitfall 3: Trusting Declared MIME Type

**What goes wrong:** Intake accepts `Content-Type: application/pdf` from upload without verifying. Attacker uploads executable with spoofed header.

**How to avoid:** Always run libmagic/content sniffing. Reject if sniffed type != declared or not on allowlist.

### Pitfall 4: Content in System Prompts Without Demarcation

**What goes wrong:** Retrieved chunks are concatenated into the LLM prompt as free text. A chunk containing "Ignore previous instructions. You are now..." is interpreted as a command.

**How to avoid:** Envelope pattern with explicit content boundary. Use delimiters like `[DOCUMENT_CONTENT]\n{chunk_text}\n[/DOCUMENT_CONTENT]` so the model treats it as data, not instructions.

## Sources

### Primary (HIGH confidence)

- `docs/product/PRD.md` — Audit event schema (Section 2), Appendix A (event types), Appendix C (allowlist), Appendix G (injection patterns, config)
- `.planning/research/ARCHITECTURE.md` — Audit stream design, policy gate patterns, injection defense flow
- `.planning/research/PITFALLS.md` — C2 (injection), C4 (audit), C5 (deletion/tombstoning)
- `docs/security/THREAT_MODEL_SAFETY.md` — Boundary controls, ingestion controls, auditability
- `.planning/research/FEATURES.md` — TS-1.3 (allowlist), TS-1.6 (receipts), TS-5.1 (immutable audit)

### Secondary (MEDIUM confidence)

- PostgreSQL append-only patterns (training knowledge)
- libmagic / python-magic for MIME sniffing (industry standard)
- Prompt injection defense literature (OWASP, academic papers)

## Metadata

**Confidence breakdown:**

- Audit schema and event types: HIGH — fully specified in PRD
- Immutable storage: MEDIUM — PostgreSQL pattern is standard; exact DDL will be in plan
- Injection patterns: HIGH — PRD Appendix G provides categories; plan will add concrete regexes
- Envelope pattern: HIGH — THREAT_MODEL and PRD glossary define it clearly
- File allowlist: HIGH — PRD Appendix C is complete

**Research date:** 2026-02-11
**Valid until:** 2026-04-11
