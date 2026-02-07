# Threat Model + Safety Controls (Document ETL → RAG)

## Core threat statement
Documents are untrusted inputs. They can contain hidden instructions, malicious payloads, or adversarial text intended to subvert downstream models.

## Primary risks
1. **Prompt/document injection**: instructions embedded in docs that try to control the model or tools
2. **Cross-tenant data leakage**: shared infra or logging surfaces exposing other tenants
3. **Citation fraud**: model returns citations not present in the corpus
4. **Silent extraction loss**: parsing drops critical tables/clauses without visibility
5. **Supply chain / dependency drift**: offline bundle breaks as dependencies change

## Controls (required)
### A) Boundary controls
- Strict separation between: *content* vs *system/tool instructions*
- Never include raw doc text inside system prompts
- Create a “content-only” channel for retrieved slices

### B) Ingestion controls
- File allowlist + MIME verification
- Malware scanning
- Checksums and immutable receipts

### C) Parsing + chunking controls
- Deterministic chunk IDs
- Store offsets (doc_id, page, start_char, end_char)
- Preserve tables with structured representation

### D) Retrieval + output controls
- “Cite-only-from-retrieval”: answer must be backed by stored slices
- Block/flag if retrieval confidence is low (recall/coverage threshold)
- Maintain a “retrieval proof” object for every answer in legal workflows

### E) Tenancy controls
- Per-tenant keys (KMS)
- Per-tenant storage namespaces
- Network isolation and strict IAM boundaries

### F) Auditability
- Immutable audit log for: ingestion → normalization → embedding model/version → index write → retrieval
- Version pins for models and pipelines
