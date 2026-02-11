# Policy Engine Implementation Plan

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** IMPL-05  
**References:** [PRD.md](PRD.md) Section 2.3 (Phase C); [DOCUMENT_SAFETY.md](DOCUMENT_SAFETY.md) Section 1; [AUDIT_ARCHITECTURE.md](AUDIT_ARCHITECTURE.md) Section 1.2; [PARSING_PIPELINE_PLAN.md](PARSING_PIPELINE_PLAN.md)

---

## 1. Overview

The policy engine applies three sequential governance gates to every parsed document before embedding. **Hard constraint:** All three gates run BEFORE embedding. Malicious or sensitive content must never reach the vector store.

**Input:** Canonical structured document JSON from parsing pipeline (chunks with text, element_type, page, offsets).  
**Output:** Policy-enriched chunks with PII, classification, and injection metadata. Chunks that pass all gates (or are FLAGged) proceed to embedding; BLOCKed or QUARANTINEd chunks do not.

**Reference:** PRD Section 2.3, DOCUMENT_SAFETY Section 1.6 (gate ordering).

---

## 2. Gate 1: PII/PHI Detection

### 2.1 PII Types (PRD Appendix G)

| Code | Description |
|------|-------------|
| SSN | Social Security Number |
| DOB | Date of Birth |
| EMAIL | Email Address |
| PHONE | Phone Number |
| NAME | Personal Name |
| ADDRESS | Physical Address |
| MEDICAL_RECORD | Medical Record Number |
| FINANCIAL_ACCOUNT | Bank/Financial Account |
| PASSPORT | Passport Number |
| DRIVERS_LICENSE | Driver's License |

Tenant config `pii_types` specifies which to detect (subset of above). Default: `["SSN", "DOB", "EMAIL"]`.

### 2.2 Detection

- **Method:** NER-based scanning (spaCy en_core_web_lg or Presidio analyzer per TECH_DECISIONS).
- **Scope:** All chunk text content.
- **Output:** PII types found, span offsets, action taken per span.

**Never record actual PII content in metadata or audit.** Only type names (e.g., `["SSN", "EMAIL"]`).

### 2.3 Per-Tenant Actions

| config.pii_policy | Action | Chunk text | Embedding |
|-------------------|--------|------------|-----------|
| REDACT | Replace PII span with `[REDACTED:TYPE]` (e.g., `[REDACTED:SSN]`). Store originals encrypted (admin API only). | Modified | Yes |
| FLAG | Mark chunk metadata with PII types found. Do not modify text. | Unchanged | Yes |
| BLOCK | Quarantine entire document. No chunks proceed. | — | No |

### 2.4 Metadata Fields

- `pii_scan_result`: `clean` | `pii_found` | `redacted` | `blocked`
- `pii_types_found`: array of type codes (never content)
- `pii_action_taken`: `none` | `redacted` | `flagged` | `blocked`

---

## 3. Gate 2: Document Classification

### 3.1 Categories

| Category | Description |
|----------|-------------|
| contract | Contracts, agreements |
| invoice | Invoices, billing |
| SOP | Standard operating procedures |
| policy | Policy documents |
| correspondence | Letters, emails |
| legal_filing | Legal filings, court docs |
| other | Unclassified or low confidence |

### 3.2 Two-Stage Classification

**Stage 1 — Rule-based:**
- Filename patterns: `*_contract_*.pdf`, `*invoice*.xlsx`
- Header keywords: "AGREEMENT", "INVOICE", "STANDARD OPERATING PROCEDURE"
- Metadata fields from parsing

**Stage 2 — ML-assisted (if rule-based produces no match or low confidence):**
- Zero-shot or few-shot classifier
- Records: classification, confidence (0.0–1.0), classifier_version

### 3.3 Review Queue Routing

If `confidence < config.classification_threshold` (default 0.7):
- Route to human review queue (if `classification_review_enabled: true`)
- If review queue unavailable: proceed with `classification: "other"`, `human_override: false`

### 3.4 Metadata Fields

- `classification`: category string
- `classification_confidence`: number 0.0–1.0
- `classifier_version`: string
- `human_override`: boolean

---

## 4. Gate 3: Injection Defense

**Reference:** DOCUMENT_SAFETY Section 1 (patterns, heuristic scorer, decision tree).

### 4.1 Pattern Scanner

Apply regex patterns from DOCUMENT_SAFETY Section 1.2:
- Direct instruction override, role assumption, delimiter injection, etc.
- Homoglyph detection (Unicode NFKC, mixed script)
- Invisible character detection (U+200B, U+202E, etc.)

Store pattern category names matched (e.g., `["ignore_previous", "role_assumption"]`). **Never store matched text content.**

### 4.2 Heuristic Scorer

**Score range:** 0.0 to 1.0

**Factors (DOCUMENT_SAFETY 1.3):**
- Pattern match count (weight 0.4)
- Control/invisible char ratio (0.3)
- Instruction-like structure (0.2)
- Length anomaly (0.1)

Use tenant thresholds: `injection_flag_threshold` (default 0.3), `injection_quarantine_threshold` (default 0.7).

### 4.3 Decision Tree

| Score | Action | Metadata | Embedding |
|-------|--------|----------|-----------|
| < 0.3 | PASS | None | Yes |
| 0.3 – 0.7 | FLAG | injection_score, patterns_matched[], action=flag | Yes |
| ≥ 0.7 | QUARANTINE | injection_score, patterns_matched[], action=quarantine | **No** |

**Per-chunk vs per-document quarantine:** Default per-chunk. Tenant config can enable per-document (if any chunk ≥ 0.7, quarantine entire document).

### 4.4 Metadata Fields

- `injection_score`: number 0.0–1.0
- `injection_patterns_matched`: array of pattern category names
- `injection_action_taken`: `pass` | `flag` | `quarantine`

---

## 5. Deterministic Chunk IDs

Chunk IDs are assigned in the parsing pipeline (PARSING_PIPELINE_PLAN). Policy engine **confirms** they are stable:

```
chunk_id = hash(doc_id + page + start_char + end_char)
```

Policy-enriched output must preserve the same chunk_id for each chunk. No reassignment.

---

## 6. Policy-Enriched Chunk Schema (Pydantic)

```python
from pydantic import BaseModel
from typing import Literal

class ChunkOffsets(BaseModel):
    page: int
    start_char: int
    end_char: int

class PolicyEnrichedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    tenant_id: str
    text: str  # May contain [REDACTED:TYPE] if PII redacted
    metadata: dict  # pii_*, classification*, injection_*
    offsets: ChunkOffsets
    element_type: str
    section_title: str | None = None
```

**metadata keys:** pii_scan_result, pii_types_found, pii_action_taken, classification, classification_confidence, classifier_version, human_override, injection_score, injection_patterns_matched, injection_action_taken.

---

## 7. Gate Execution Order

1. Gate 1 (PII) → Gate 2 (Classification) → Gate 3 (Injection)
2. If Gate 1 BLOCK: stop, quarantine document, emit DOCUMENT_QUARANTINED, do not run Gate 2 or 3.
3. If Gate 3 QUARANTINE (per-chunk): exclude chunk from embedding; other chunks may proceed.
4. After all gates: attach metadata to each passing chunk, enqueue embedding job.

---

## 8. Audit Events

**Reference:** AUDIT_ARCHITECTURE Section 1.2.

| Event Type | Trigger |
|------------|---------|
| POLICY_GATE_PASSED | Document/chunk passes a gate |
| POLICY_GATE_FAILED | Document/chunk fails (PII BLOCK, injection QUARANTINE) |
| DOCUMENT_QUARANTINED | PII BLOCK or injection score ≥ quarantine threshold |
| PII_DETECTED | PII found (always emit; details: pii_types only, never content) |

**details fields:** gate (pii/classification/injection), result_summary, action_taken, injection_score (for injection), pii_types_found (for PII).

---

## 9. Job Input and Output

**Input:** Policy job from parsing pipeline:
```json
{"doc_id": "...", "file_id": "...", "tenant_id": "...", "storage_path": "normalized/.../structured.json"}
```

**Output:** Policy-enriched chunks (for passing chunks only). Enqueue embedding job with list of chunk_ids and enriched metadata.

---

## 10. Online vs Offline Mode

Policy logic is **identical** in both modes. PII NER and classification models may be:
- Online: Same (spaCy/Presidio typically local)
- Offline: Bundled in container, no external API

No mode branching in policy gate logic.

---

## 11. Implementation Checklist

- [ ] Gate 1: PII NER (spaCy/Presidio), tenant actions (REDACT/FLAG/BLOCK)
- [ ] Gate 2: Rule-based + ML classification, review queue routing
- [ ] Gate 3: Injection pattern scanner (DOCUMENT_SAFETY patterns), heuristic scorer
- [ ] Per-tenant config loading (pii_policy, injection thresholds, classification_threshold)
- [ ] Chunk ID passthrough (no reassignment)
- [ ] Audit events (POLICY_GATE_PASSED, POLICY_GATE_FAILED, DOCUMENT_QUARANTINED, PII_DETECTED)
- [ ] Embedding job enqueue for passing chunks
