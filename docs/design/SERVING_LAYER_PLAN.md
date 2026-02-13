# Serving Layer (RAG API) Implementation Plan

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** IMPL-07  
**References:** [PRD.md](PRD.md) Section 2.5 (Phase E), Section 5.5 (Query API); [AUDIT_ARCHITECTURE.md](AUDIT_ARCHITECTURE.md) Section 1.2; [TECH_DECISIONS.md](TECH_DECISIONS.md)

---

## 1. Overview

The serving layer handles RAG retrieval queries: authenticate, embed query, vector search, fetch source slices, build retrieval proof, and optionally generate answers with cite-only-from-retrieval enforcement.

**Endpoint:** `POST /api/v1/query/{tenant_id}/search`

**Reference:** PRD Section 2.5, Section 5.5.

---

## 2. Request Flow

| Step | Action | On Failure |
|------|--------|------------|
| 1 | Authenticate JWT | 401 |
| 2 | Verify query scope, tenant_id match | 403 |
| 3 | Check tenant state (ACTIVE) | 403 TENANT_SUSPENDED |
| 4 | Rate limit (1000/min per tenant) | 429 |
| 5 | Embed query (same model+version as index) | 500 |
| 6 | Vector search (Qdrant ANN, metadata filters) | — |
| 7 | Fetch source slices (RDB, object store) | — |
| 8 | Build retrieval proof | — |
| 9 | Optional: generate answer (cite-only) | — |
| 10 | Emit RETRIEVAL_EXECUTED | — |

---

## 3. Embed Query

**Constraint:** Use the **same** embedding model and version used for indexing. If index was built with Nomic v1.5, query must use Nomic v1.5. If index was built with text-embedding-3-small, query must use that.

**Dimensions:** 768 (assert before search).

**model_version_match:** Compare query embedding model/version with index metadata. If mismatch: return `model_version_match: false` and a warning. Degraded response—ranking may be suboptimal.

---

## 4. Vector Search

**Store:** Qdrant collection `tenant_{tenant_id}`

**Operation:** ANN (Approximate Nearest Neighbor) search. Cosine similarity.

**Metadata filters:** Apply from request:
- `filters.classification`
- `filters.date_range` (ingestion date)
- `filters.doc_ids` (restrict to documents)

**top_k:** Default 5, max 50 (from tenant config `retrieval_top_k_max`).

**Output:** chunk_ids with similarity scores.

---

## 5. Fetch Source Slices

For each returned chunk_id:
- **RDB:** Fetch chunk text, doc_id, page, start_char, end_char, classification, policy metadata
- **Object store:** Fetch original filename, lineage (parser versions, raw_sha256)
- **Index metadata:** embed_model, embed_version for provenance

---

## 6. Retrieval Proof Object Schema

```json
{
  "query_id": "01957a3c-8b2e-7000-a000-000000000010",
  "tenant_id": "tenant_abc",
  "chunks": [
    {
      "chunk_id": "chk_a1b2c3d4",
      "doc_id": "doc_01957a3c",
      "original_filename": "contract_2024.pdf",
      "text": "The payment terms specify net-30...",
      "page": 3,
      "start_char": 4520,
      "end_char": 4890,
      "similarity_score": 0.91,
      "classification": "contract",
      "embed_model": "text-embedding-3-small",
      "embed_version": "2024-01-25",
      "source_sha256": "a1b2c3d4e5f67890..."
    }
  ],
  "timestamp": "2026-02-08T15:00:00Z",
  "model_version_match": true,
  "generation": null
}
```

**Purpose:** Verifiable provenance. Each chunk links to source document with byte offsets, model version, and content hash.

---

## 7. Cite-Only-From-Retrieval

**Hard constraint:** If answer generation is enabled, every claim in the generated answer must reference a chunk_id from the retrieval proof. Ungrounded text must be flagged or suppressed.

**Enforcement:**
1. Parse generated answer for citation markers (e.g., `[chk_a1b2c3d4]`)
2. Verify each cited chunk_id exists in retrieval proof
3. Identify ungrounded spans (text not backed by citation)
4. Either: suppress ungrounded text, or flag with `ungrounded_claims: [...]`

**config.generation_suppress_ungrounded:** If true, strip ungrounded text. If false, include but flag.

---

## 8. API Specification

### POST /api/v1/query/{tenant_id}/search

**Auth:** Bearer JWT, `query` scope. tenant_id from path must match token.

**Rate limit:** 1000 req/min per tenant.

**Request body:**
```json
{
  "query_text": "What are the payment terms in the 2024 contract?",
  "top_k": 5,
  "filters": {
    "classification": "contract",
    "date_range": {"start": "2024-01-01", "end": "2024-12-31"},
    "doc_ids": ["doc_01957a3c"]
  }
}
```

**Response (200):** Retrieval proof object (chunks, timestamp, model_version_match). If generation enabled and requested: include `generation.answer`, `generation.cited_chunks`, `generation.ungrounded_claims`.

---

## 9. Audit Events

| Event Type | Trigger |
|------------|---------|
| RETRIEVAL_EXECUTED | RAG retrieval completed (chunk_count, chunk_ids in details; never query text or content) |
| GENERATION_EXECUTED | Answer generated with citations |

**Reference:** AUDIT_ARCHITECTURE Section 1.2. Audit must not contain query text or chunk content.

---

## 10. Online vs Offline Mode

| Aspect | Online | Offline |
|--------|--------|---------|
| Embedding for query | OpenRouter | Nomic local |
| Vector store | Qdrant (same) | Qdrant (same) |
| Retrieval flow | Identical | Identical |

Same code path; embedding endpoint from config.

---

## 11. Implementation Checklist

- [ ] JWT validation, query scope, tenant check
- [ ] Rate limiting (Redis)
- [ ] Query embedding (same model as index)
- [ ] model_version_match check
- [ ] Qdrant vector search with metadata filters
- [ ] Source slice fetch (RDB + object store)
- [ ] Retrieval proof assembly
- [ ] Optional generation with cite-only enforcement
- [ ] RETRIEVAL_EXECUTED audit event
- [ ] Error responses (401, 403, 404, 429, 500)
