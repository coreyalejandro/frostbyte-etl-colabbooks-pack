# Embedding and Indexing Implementation Plan

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** IMPL-06  
**References:** [PRD.md](PRD.md) Section 2.4 (Phase D); [TECH_DECISIONS.md](TECH_DECISIONS.md); [AUDIT_ARCHITECTURE.md](AUDIT_ARCHITECTURE.md) Section 1.2; [STORAGE_LAYER_PLAN.md](STORAGE_LAYER_PLAN.md)

---

## 1. Overview

The embedding and indexing phase generates 768-dimensional vectors for all policy-approved chunks and writes them to three stores: object store (verify canonical JSON exists), relational database (chunk metadata), and vector store (Qdrant). Both online and offline modes lock to 768 dimensions.

**Input:** Policy-enriched chunks from policy engine.  
**Output:** Index metadata records; vectors in Qdrant; chunk metadata in PostgreSQL.

**Reference:** PRD Section 2.4, TECH_DECISIONS (768d lock, OpenRouter, Nomic).

---

## 2. Online Mode: OpenRouter Embeddings

**Endpoint:** `FROSTBYTE_EMBEDDING_ENDPOINT` (e.g., OpenRouter `/api/v1/embeddings`)

**Model:** `openai/text-embedding-3-small` with `dimensions: 768`

**Request pattern:**

```json
{
  "model": "openai/text-embedding-3-small",
  "input": ["chunk text 1", "chunk text 2", ...],
  "dimensions": 768
}
```

**Response:** `data[].embedding` — array of 768 floats per chunk.

**Reference:** TECH_DECISIONS Section 2.1, online manifest.

---

## 3. Offline Mode: Nomic Embed-Text

**Model:** Nomic embed-text v1.5 (768d native)

**Deployment:** Local container (GPT4All-based or equivalent). Application config points embedding service to local endpoint instead of OpenRouter.

**Request:** Same interface as online—batch of texts, returns 768d vectors. No `dimensions` parameter (native 768d).

**Reference:** TECH_DECISIONS Section 2.1, Section 3 (Nomic v1.5), offline manifest.

---

## 4. Dimension Assertion

**CRITICAL:** Before writing to Qdrant, assert every vector has exactly 768 dimensions.

```python
def assert_dimensions(vectors: list[list[float]], expected: int = 768) -> None:
    for i, v in enumerate(vectors):
        if len(v) != expected:
            raise DimensionMismatchError(f"Vector {i} has {len(v)} dims, expected {expected}")
```

If mismatch: halt, alert ops, do not write. This is a configuration error.

---

## 5. Three-Store Write

### 5.1 Store 1: Object Store (MinIO)

- **Action:** Verify canonical JSON exists at `normalized/{tenant_id}/{doc_id}/structured.json`
- **No new write** — parsing pipeline already wrote it. Embedding phase confirms presence for integrity check.

### 5.2 Store 2: Relational Database (PostgreSQL)

**Table:** `chunks` (per-tenant schema or tenant-scoped)

**Columns:** chunk_id, doc_id, tenant_id, text, page, start_char, end_char, classification, pii_scan_result, injection_score, embed_model, embed_version, indexed_at, config_version

**Lineage:** raw_sha256, parser versions, policy config version.

### 5.3 Store 3: Vector Store (Qdrant)

**Collection:** `tenant_{tenant_id}` (per STORAGE_LAYER_PLAN)

**Point structure:**

- `id`: chunk_id
- `vector`: 768-dimensional embedding
- `payload`: doc_id, tenant_id, classification, page, chunk_id

**Metadata filters:** For retrieval: doc_id, tenant_id, classification, page.

---

## 6. Write Integrity Verification

After all three writes:

1. Compute SHA-256 of written data (vector bytes, DB row, object store path)
2. Compare with pre-write computed hash
3. If mismatch: rollback (delete from Qdrant, delete from RDB), mark job failed, retry entire batch

**Rollback order:** Vector store → RDB (object store read-only for this phase).

---

## 7. Index Metadata Record Schema

```json
{
  "chunk_id": "chk_a1b2c3d4",
  "doc_id": "doc_01957a3c",
  "tenant_id": "tenant_abc",
  "embed_model": "text-embedding-3-small",
  "embed_version": "2024-01-25",
  "embed_dimensions": 768,
  "vector_sha256": "e7f8a9b0c1d2...",
  "indexed_at": "2026-02-08T14:40:00Z"
}
```

**Reference:** PRD Section 2.4.

---

## 8. Retry and Dead-Letter

**Retry policy:** 3 attempts, exponential backoff (10s, 60s, 300s).

**On embedding API failure:** Retry. After max retries: mark `embed_failed`, route to DLQ, emit EMBEDDING_FAILED.

**On partial write (one store succeeds, others fail):** Compensating rollback. Retry entire batch.

**On dimension mismatch:** No retry. Alert immediately.

---

## 9. Audit Events

| Event Type | Trigger |
|------------|---------|
| DOCUMENT_EMBEDDED | All chunks for a document embedded |
| INDEX_WRITTEN | Chunk batch written to all three stores |
| EMBEDDING_FAILED | Embedding API failed after retries |

**Reference:** AUDIT_ARCHITECTURE Section 1.2.

---

## 10. Online vs Offline Mode Differences

| Aspect | Online | Offline |
|--------|--------|---------|
| Embedding API | OpenRouter (external) | Nomic container (local) |
| Model | text-embedding-3-small (768d via param) | Nomic embed-text v1.5 (768d native) |
| Configuration | FROSTBYTE_EMBEDDING_ENDPOINT | FROSTBYTE_EMBEDDING_ENDPOINT (local URL) |
| Retries | Network failures, rate limits | Local failures only |

**Mode parity:** Same code path; config determines endpoint. Both produce 768d vectors.

**Explicit divergence (TECH_DECISIONS):** Vectors from different models are semantically similar but not identical. Cross-mode search works but may produce different ranking. Full re-index recommended when switching modes.

---

## 11. Job Enqueue (Downstream)

After successful indexing: no further job enqueue (pipeline complete for document). Serving layer responds to queries.

---

## 12. Implementation Checklist

- [ ] Embedding client abstraction (online vs offline endpoint)
- [ ] Batch embed (OpenRouter/Nomic API calls)
- [ ] Dimension assertion (768)
- [ ] Object store verification (canonical JSON exists)
- [ ] PostgreSQL chunk metadata write
- [ ] Qdrant vector write (chunk_id, payload)
- [ ] Write integrity verification, rollback on mismatch
- [ ] Retry with exponential backoff
- [ ] Audit events (DOCUMENT_EMBEDDED, INDEX_WRITTEN, EMBEDDING_FAILED)
- [ ] Model version recording in metadata
