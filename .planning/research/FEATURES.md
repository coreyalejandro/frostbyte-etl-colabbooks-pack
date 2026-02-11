# Feature Landscape: Multi-Tenant Document ETL Pipeline for Regulated Industries

**Domain:** Enterprise document ETL pipelines serving legal, compliance, and regulated enterprise verticals
**Researched:** 2026-02-08
**Overall confidence:** MEDIUM — based on training knowledge of enterprise document processing platforms (Unstructured, LlamaIndex, Haystack, Docling, Qdrant, Weaviate), regulated industry compliance requirements (SOC 2, GDPR, HIPAA), and multi-tenant architecture patterns. Web research tools were unavailable; findings are cross-referenced against existing project artifacts (THREAT_MODEL_SAFETY.md, ETL_PIPELINE_PROPOSAL.md, CUSTOMER_JOURNEY_MAP.md) which provide strong domain grounding.

---

## Table Stakes

Features users and regulators expect. Missing any of these = product rejected by procurement, compliance, or the "Dana" persona.

### TS-1: Intake and Ingestion

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| TS-1.1 | **Manifest-based batch intake** | Vendors ship documents in batches with manifests; without manifest parity checks, there is no proof of complete delivery. Dana's first question: "Did you receive everything?" | Medium | None | Manifest format must be vendor-friendly (CSV/JSON). Must support re-submission of failed items without full re-upload. |
| TS-1.2 | **Checksum verification (SHA-256)** | Integrity proof that files were not corrupted or tampered with in transit. Required for audit trails in regulated industries. | Low | TS-1.1 | Checksums become the immutable anchor for provenance chains downstream. |
| TS-1.3 | **File-type allowlisting + MIME verification** | Untrusted inputs demand strict type gates. Prevents polyglot files, disguised executables, and unsupported formats from entering the pipeline. | Low | None | Allowlist must be configurable per tenant. MIME-sniffing (libmagic) required in addition to extension checks. |
| TS-1.4 | **Malware scanning on ingestion** | Documents are untrusted inputs. ClamAV or equivalent must scan every file before any parsing occurs. Non-negotiable for enterprise procurement. | Medium | None | Must work offline (ClamAV with local signature DB). Scan results logged to audit trail. |
| TS-1.5 | **Tenant-scoped authentication and authorization** | Every API call and upload must be authenticated to a specific tenant. No anonymous ingestion. | Medium | Tenant provisioning | API keys or mTLS per tenant. Must support key rotation without downtime. |
| TS-1.6 | **Immutable intake receipts** | Every file received produces an append-only receipt (tenant_id, file_id, sha256, timestamp, source, status). This is the foundation of the audit chain. | Medium | TS-1.2 | Receipt must be queryable by vendor for self-service status checks. |
| TS-1.7 | **Rate limiting and quotas** | Prevent a single tenant from overwhelming shared infrastructure. Required for fair resource allocation and DoS prevention. | Low | TS-1.5 | Per-tenant configurable limits. Must return clear error messages, not silent drops. |

### TS-2: Document Parsing and Structuring

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| TS-2.1 | **PDF parsing with layout preservation** | PDFs are the dominant document format in legal and enterprise. Parsing must preserve reading order, headers, sections, and page boundaries. | High | None | Docling + Unstructured as primary parsers. Must handle scanned PDFs (OCR path) and native PDFs (text extraction path). |
| TS-2.2 | **Table extraction with structured output** | Contracts, financial docs, and SOPs contain critical tabular data. Tables must be extracted as structured objects, not flattened text. | High | TS-2.1 | Table extraction accuracy is a top vendor complaint. Must preserve row/column structure and cell content. |
| TS-2.3 | **Canonical structured document format** | All downstream consumers (storage, retrieval, analytics) need a single normalized schema. Without this, every consumer builds ad-hoc parsing. | Medium | TS-2.1 | JSON schema with: sections, tables, figures, reading_order, offsets (doc_id, page, start_char, end_char). |
| TS-2.4 | **Deterministic chunking with stable IDs** | Chunks must be reproducible across re-runs. If the same document produces different chunks on different runs, vector indices become inconsistent and audit trails break. | Medium | TS-2.3 | Chunk IDs derived from content hash + position, not random UUIDs. Enables idempotent reprocessing. |
| TS-2.5 | **Document lineage pointers** | Every chunk must trace back to its source: raw file -> normalized doc -> section -> chunk, with byte offsets. Without this, retrieval proofs are impossible. | Medium | TS-2.3, TS-2.4 | This is the backbone of verifiable RAG. Legal use cases require "show me exactly where this came from." |
| TS-2.6 | **Parse failure visibility** | When parsing drops content (unreadable pages, corrupt tables, unsupported elements), the system must report exactly what was dropped and why. Silent data loss is unacceptable. | Medium | TS-2.1 | Feeds directly into the Vendor Acceptance Report. Dana needs: "3 tables on page 7 could not be extracted because [reason]." |

### TS-3: Data Governance

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| TS-3.1 | **PII/PHI detection** | Regulated industries (HIPAA, GDPR, CCPA) require knowing where personal data exists in documents. Detection must run before storage. | High | TS-2.3 | Use NER models (spaCy, Presidio) or regex-based detectors. Must detect: names, SSN, DOB, addresses, email, phone, medical terms. Configurable per tenant/jurisdiction. |
| TS-3.2 | **Configurable redaction policies** | Different tenants and jurisdictions have different rules. Some require full redaction, others masking, others flagging-only. Must be policy-driven, not hardcoded. | High | TS-3.1 | Policies defined per tenant. Redaction must be reversible (store original in encrypted form) or irreversible (true deletion) based on policy. |
| TS-3.3 | **Document classification** | Documents must be categorized (contract, invoice, SOP, correspondence, etc.) for routing, policy application, and retention rules. | Medium | TS-2.3 | Classification drives which governance policies apply. Can start with rule-based, evolve to ML-based. |
| TS-3.4 | **Retention policy enforcement** | Regulated industries require documents to be retained for specific periods and then provably deleted. Must be automated, not manual. | Medium | TS-3.3, Storage | Retention schedules configurable per tenant and document class. Deletion must cascade across all stores (object, relational, vector) and produce deletion receipts. |

### TS-4: Storage and Tenant Isolation

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| TS-4.1 | **Per-tenant isolated storage namespaces** | Tenant A's data must never be accessible by Tenant B's queries, APIs, or admin interfaces. Isolation by construction, not just by policy/ACL. | High | Tenant provisioning | Object store: per-tenant buckets/prefixes. Relational DB: per-tenant schemas or databases. Vector store: per-tenant collections. |
| TS-4.2 | **Per-tenant encryption keys (KMS)** | Even if storage isolation fails, encryption keys ensure data is inaccessible. Required for SOC 2 and most enterprise security questionnaires. | High | TS-4.1 | Keys managed via KMS (HashiCorp Vault or cloud KMS). Key rotation must not require re-encryption of all data immediately (envelope encryption pattern). |
| TS-4.3 | **Three-store architecture (object + relational + vector)** | Raw files in object store, metadata/lineage/governance in relational, embeddings in vector. This separation of concerns is standard for document ETL. | Medium | None | All three stores must respect tenant isolation boundaries. Cross-store consistency must be maintained (or reconcilable). |
| TS-4.4 | **Backup and disaster recovery per tenant** | Regulated industries require documented backup and recovery procedures. Must be per-tenant (one tenant's restore must not affect another). | High | TS-4.1 | RPO/RTO targets must be configurable per tenant SLA. Backup integrity verified via checksums. |

### TS-5: Audit and Compliance

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| TS-5.1 | **Immutable append-only audit log** | Every action on every document must be logged immutably: ingestion, parsing, enrichment, storage, retrieval, deletion. This is table stakes for legal and compliance use cases. | High | All pipeline phases | Audit log must be tamper-evident (hash chain or write-once storage). Must support export for external auditors. |
| TS-5.2 | **Full provenance chain** | For any chunk served via retrieval, the system must produce: raw_file -> normalized_doc -> section -> chunk -> embedding_model_version -> vector_index_write -> retrieval_event. | High | TS-2.5, TS-5.1 | This is what makes RAG "legal-grade." Without provenance, retrieval results are unverifiable opinions. |
| TS-5.3 | **Model and pipeline version pinning** | Audit trails must record which version of every model (parser, classifier, embedding) and pipeline was used. Reproducibility requires knowing exact versions. | Medium | TS-5.1 | Critical for regulated environments where "why did the output change?" must be answerable. |
| TS-5.4 | **Audit log export and query API** | Auditors and compliance teams need to query and export logs without engineering involvement. Must support common query patterns (by tenant, date range, document, event type). | Medium | TS-5.1 | Consider structured log format (JSON Lines) exportable to SIEM tools. |

### TS-6: Security

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| TS-6.1 | **Prompt/document injection defense** | Documents can contain hidden instructions that subvert downstream LLMs. Content must never be mixed with system instructions. Strict boundary between content and control plane. | High | TS-2.3 | Content-only retrieval channel. Never insert raw document text into system prompts. Sanitize Unicode control characters, invisible text, and embedded instructions. |
| TS-6.2 | **Network isolation between tenants** | Tenant workloads must not be able to communicate with each other. Network segmentation is required, not optional. | High | TS-4.1 | On Hetzner: per-tenant VPCs or firewall rules. In Docker: network isolation via Docker networks. |
| TS-6.3 | **Tenant kill-switch** | If a tenant is compromised or breached, the system must be able to instantly disable all access to that tenant's data and processing without affecting other tenants. | Medium | TS-4.1, TS-1.5 | Must disable: API access, retrieval, processing jobs, and admin access. Must be reversible. |
| TS-6.4 | **Encryption at rest and in transit** | TLS for all network communication. Encryption at rest for all stores. Non-negotiable for any enterprise deployment. | Medium | TS-4.2 | TLS 1.3 minimum. At-rest encryption using tenant-specific keys. |

### TS-7: Monitoring and Observability

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|--------------|------------|--------------|-------|
| TS-7.1 | **Pipeline job status tracking** | Dana and operations teams need to know: is my batch processing? What stage is it at? What failed? Real-time or near-real-time status. | Medium | All pipeline phases | Status must be queryable per tenant. Must show: queued, processing, completed, failed, with counts per stage. |
| TS-7.2 | **Error alerting and notification** | When ingestion fails, parsing drops content, or storage writes error, the system must alert operators proactively. Silent failures are unacceptable. | Medium | TS-7.1 | Configurable alert channels (email, webhook, Slack). Alert severity levels. Must not leak tenant data in alerts. |
| TS-7.3 | **Resource utilization metrics** | CPU, memory, storage, and processing throughput per tenant. Required for capacity planning and SLA compliance. | Low | None | Prometheus/Grafana or equivalent. Per-tenant dashboards. |

---

## Differentiators

Features that set the product apart from commodity ETL pipelines. Not expected by default, but valued by sophisticated buyers and demonstrate enterprise maturity.

### D-1: Customer-Facing Transparency

| # | Feature | Value Proposition | Complexity | Dependencies | Notes |
|---|---------|-------------------|------------|--------------|-------|
| D-1.1 | **Vendor Acceptance Report (auto-generated)** | Dana gets a complete report after every batch: what was received, what was parsed, what was dropped, what was classified, what was indexed. This eliminates the "black box" problem and is the primary trust-builder. | Medium | TS-1.6, TS-2.6, TS-3.1 | Most competitors provide at best a success/failure count. A structured, per-file breakdown with human-readable explanations is a major differentiator. See `templates/VENDOR_ACCEPTANCE_REPORT.md`. |
| D-1.2 | **Parse preview with diff** | Before committing parsed output to storage, show the vendor a preview: "Here is what we extracted from your document. Confirm or flag issues." This catches extraction errors early. | High | TS-2.3, TS-2.6 | Optional human-in-the-loop gate. Can be async (generate preview, vendor reviews within N hours). Reduces rework cycles dramatically. |
| D-1.3 | **Retrieval proof objects** | For every RAG-generated answer, produce a proof object: the exact source chunks, their byte offsets in the original document, the similarity scores, and the embedding model version. Makes retrieval auditable and disputable. | High | TS-5.2, TS-2.5 | This is what turns generic RAG into "legal-grade verifiable RAG." Competitors rarely provide this level of provenance. |
| D-1.4 | **Self-service tenant status dashboard** | Dana can check: current batch status, historical acceptance reports, storage utilization, retention schedules — without filing a support ticket. | Medium | TS-7.1, D-1.1 | White-labeled, read-only dashboard. Must be tenant-scoped (Dana sees only her data). |

### D-2: Dual-Mode Operation

| # | Feature | Value Proposition | Complexity | Dependencies | Notes |
|---|---------|-------------------|------------|--------------|-------|
| D-2.1 | **Offline/air-gapped Docker bundle** | Many regulated environments (government, defense, healthcare) cannot send data to external APIs. A self-contained Docker Compose bundle that runs the full pipeline with zero outbound network calls is a hard differentiator. | High | Local embeddings (Nomic), local parsing, local storage | Most competitors are cloud-only or cloud-first. True air-gapped operation with feature parity is rare and valuable. Requires local embedding model (Nomic embed-text), local ClamAV signatures, local NER models. |
| D-2.2 | **Signed export bundles** | Offline pipeline produces signed, integrity-verified export packages (normalized JSON + vector index snapshots) that can be imported into the online system or another offline instance. Chain of custody preserved. | High | D-2.1, TS-1.2 | Signing proves: this output was produced by this pipeline version, from these inputs, at this time. Critical for legal chain-of-custody scenarios. |
| D-2.3 | **Mode parity with explicit divergence documentation** | Online and offline modes must have documented feature parity or explicit documentation of what differs. "Works online but not offline" without documentation is a trust-killer. | Medium | D-2.1 | Compatibility matrix: which features work in which mode, which embedding models are available, what hardware is required for offline. |
| D-2.4 | **Offline signature and model update mechanism** | Air-gapped systems still need security signature updates (ClamAV) and model updates. A secure, verifiable update mechanism (USB/sneakernet with signed packages) is required. | Medium | D-2.1, TS-1.4 | Without this, offline deployments become security liabilities over time. |

### D-3: Advanced Governance

| # | Feature | Value Proposition | Complexity | Dependencies | Notes |
|---|---------|-------------------|------------|--------------|-------|
| D-3.1 | **Configurable policy-as-code governance** | Governance rules (PII handling, retention, classification, redaction) defined as versioned, tenant-specific policy files — not hardcoded logic. Enables per-tenant compliance postures. | High | TS-3.1, TS-3.2, TS-3.3 | Policy files can be YAML/JSON, versioned in git, auditable. Policy changes produce audit log entries. |
| D-3.2 | **Data residency enforcement** | Guarantee that a tenant's data never leaves a specific geographic region, cloud provider, or machine. Provable via architecture (not just policy). | High | TS-4.1, TS-6.2 | On Hetzner: tenant assigned to specific datacenter location. Processing and storage co-located. Particularly valuable for EU data residency (GDPR) and German BDSG compliance. |
| D-3.3 | **Automated compliance evidence generation** | Produce SOC 2 / ISO 27001 / GDPR evidence artifacts automatically from the audit log and system configuration. Reduces compliance burden from weeks to hours. | High | TS-5.1, TS-5.4 | Most platforms leave evidence generation as a manual exercise. Auto-generating control evidence from system logs is a significant differentiator. |

### D-4: Pipeline Intelligence

| # | Feature | Value Proposition | Complexity | Dependencies | Notes |
|---|---------|-------------------|------------|--------------|-------|
| D-4.1 | **Idempotent delta processing** | Reprocess only failed or changed documents/segments, not the entire batch. Reduces cost, time, and redundant work. Enables incremental vendor submissions. | Medium | TS-2.4, TS-1.2 | Requires stable chunk IDs and content-addressable storage. Diff detection via checksum comparison against previously processed versions. |
| D-4.2 | **Configurable parser chaining** | Route documents through different parser configurations based on document type, quality, or tenant preference. E.g., scanned PDFs get OCR-first path; native PDFs get direct extraction. | Medium | TS-2.1, TS-3.3 | Parser selection based on MIME type, document classification, or explicit tenant configuration. Avoids one-size-fits-all parsing failures. |
| D-4.3 | **Schema evolution and migration** | As the canonical document schema evolves, existing stored documents must be migratable without full reprocessing. Schema versioning with backward compatibility. | High | TS-2.3 | Without this, every schema change triggers expensive reprocessing of the entire corpus. Version field in every stored document enables lazy migration. |
| D-4.4 | **Quality scoring per document** | Assign a parse quality score (completeness, confidence) to each processed document. Enables vendors and operators to prioritize review of low-quality extractions. | Medium | TS-2.6 | Score based on: % of pages successfully parsed, table extraction confidence, OCR confidence, PII detection coverage. Surfaces in acceptance report. |

### D-5: Vendor Onboarding Workflow

| # | Feature | Value Proposition | Complexity | Dependencies | Notes |
|---|---------|-------------------|------------|--------------|-------|
| D-5.1 | **Sandbox tenant for trial submissions** | Before production rollout, vendors submit test batches to an isolated sandbox. Validates format compatibility, parsing quality, and workflow without risk. | Medium | TS-4.1 | Sandbox is a full tenant with all features but ephemeral storage. Reduces vendor onboarding friction and catches format issues early. |
| D-5.2 | **Vendor intake checklist (interactive)** | Guided checklist that walks Dana through: required document formats, manifest format, naming conventions, authentication setup. Eliminates ambiguity from [P1] in the journey map. | Low | None | Can be a static document initially, evolve to interactive web form. Key: be prescriptive, not open-ended. |
| D-5.3 | **Automated format compatibility testing** | When a vendor submits sample documents, automatically test: can we parse this? What's the extraction quality? Report results before the vendor commits to the full batch. | Medium | TS-2.1, D-5.1 | Runs parser on sample, produces mini acceptance report. Fast feedback loop prevents wasted effort. |

---

## Anti-Features

Features to deliberately NOT build. Common mistakes in the document ETL domain that add complexity, create security risk, or mislead users.

### AF-1: Cross-Tenant Aggregation

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Cross-tenant analytics or dashboards** | Fundamentally violates the isolation-by-construction principle. Even "anonymized" cross-tenant data creates re-identification risk and regulatory exposure. Any cross-tenant data flow, no matter how "safe," will fail enterprise security reviews. | Provide per-tenant analytics only. If aggregate insights are needed (e.g., platform health), derive them from non-tenant-specific operational metrics (job counts, latency, error rates) that contain zero document content. |

### AF-2: LLM-in-the-Loop Parsing

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Using LLMs for document parsing/structuring** | LLMs are non-deterministic. The same document produces different structures on different runs. This breaks deterministic chunking, stable IDs, audit trails, and reproducibility. Additionally, sending document content to external LLMs violates sovereignty for air-gapped deployments. | Use deterministic parsers (Docling, Unstructured) for structure extraction. Reserve LLMs for downstream retrieval/generation only, where non-determinism is acceptable and controllable. |

### AF-3: Shared Vector Index

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Single shared vector index with tenant filtering** | Metadata-filter-based tenant isolation in vector stores is fragile. One misconfigured query, one missing filter, one library bug, and Tenant A retrieves Tenant B's chunks. Filter-based isolation fails security reviews. | Per-tenant vector collections/indices. Physical isolation, not logical filtering. Higher ops cost but eliminates an entire class of data leakage. |

### AF-4: Real-Time Streaming Ingestion

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time streaming document ingestion** | Documents in this domain arrive in batches with manifests, not as continuous streams. Building streaming infrastructure adds massive complexity (exactly-once semantics, backpressure, reordering) for a use case that does not require it. Additionally, streaming makes manifest-based completeness checks impossible. | Batch-first pipeline. Accept batches, verify against manifests, process sequentially or in parallel within the batch. Support incremental batches (deltas) but not streaming. |

### AF-5: Auto-Correction of Parse Errors

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Automatic correction or "healing" of parsed content** | If the system silently "fixes" extraction errors, the corrected content may not match the source document. In legal and compliance contexts, the stored representation must faithfully represent the source, not an interpretation of it. Silent correction creates liability. | Report extraction issues in the acceptance report. Let the vendor or operator decide: re-submit a cleaner document, accept the imperfect extraction, or manually correct with full audit trail. |

### AF-6: Universal Document Support

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Claim to support "any document format"** | Every new format adds parsing complexity, test surface, and potential security attack vectors. Polyglot files and exotic formats are common malware vectors. Supporting everything means testing nothing thoroughly. | Define an explicit, tested allowlist of supported formats (PDF, DOCX, XLSX, CSV, TXT, PNG/JPG for OCR). Reject unsupported formats at the intake gateway with clear error messages. Expand the allowlist deliberately, with full test coverage for each addition. |

### AF-7: User-Facing "AI Confidence" Scores

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Exposing raw model confidence/similarity scores to end users** | Similarity scores, cosine distances, and model confidence values are meaningless to Dana. They create false precision ("0.87 confidence" sounds authoritative but is arbitrary). Users either over-trust or dismiss them. | Provide actionable categories: "High confidence match," "Partial match — review recommended," "No match found." Back these categories with thresholds tuned per use case, but hide the raw numbers from non-technical users. Internal dashboards can show raw scores for operators. |

---

## Feature Dependencies

```
Tenant Provisioning (foundation)
  |
  +---> TS-1.5 Tenant Auth -------> TS-1.7 Rate Limits
  |                                   |
  +---> TS-4.1 Storage Isolation --> TS-4.2 Per-Tenant KMS
  |       |                            |
  |       +---> TS-6.2 Network Iso    +---> TS-6.4 Encryption at Rest
  |       |
  |       +---> TS-4.4 Backup/DR
  |       |
  |       +---> D-5.1 Sandbox Tenant
  |
  +---> TS-6.3 Kill Switch

TS-1.1 Manifest Intake
  |
  +---> TS-1.2 Checksum Verification
  |       |
  |       +---> TS-1.6 Immutable Receipts --> TS-5.1 Audit Log
  |
  +---> TS-1.3 File Allowlist
  |
  +---> TS-1.4 Malware Scan

TS-2.1 PDF Parsing
  |
  +---> TS-2.2 Table Extraction
  |
  +---> TS-2.3 Canonical Schema --> TS-2.4 Deterministic Chunking
  |       |                          |
  |       +---> TS-2.5 Lineage       +---> D-4.1 Idempotent Delta
  |       |
  |       +---> TS-2.6 Parse Failure Visibility --> D-1.1 Acceptance Report
  |       |
  |       +---> TS-3.1 PII Detection --> TS-3.2 Redaction
  |       |
  |       +---> TS-3.3 Classification --> TS-3.4 Retention
  |
  +---> D-4.2 Parser Chaining

TS-5.1 Audit Log (central dependency)
  |
  +---> TS-5.2 Provenance Chain --> D-1.3 Retrieval Proofs
  |
  +---> TS-5.3 Version Pinning
  |
  +---> TS-5.4 Audit Query/Export --> D-3.3 Compliance Evidence
```

### Critical Path

The dependency graph reveals a clear critical path for implementation:

1. **Tenant provisioning and isolation** (foundation for everything)
2. **Intake gateway** (first trust boundary)
3. **Parsing and canonical schema** (core value creation)
4. **Audit log infrastructure** (must exist before any production data flows)
5. **Storage writes** (three-store architecture)
6. **Governance gates** (PII, classification, redaction)
7. **Retrieval and serving** (value delivery to end users)
8. **Customer-facing transparency** (acceptance reports, dashboards)
9. **Offline mode** (parallel workstream once online works)

---

## MVP Recommendation

For MVP, prioritize all table stakes features and one high-impact differentiator cluster:

### Phase 1: Foundation (must ship first)

1. **Tenant provisioning and isolation** (TS-4.1, TS-4.2, TS-6.2, TS-6.4)
2. **Intake gateway** (TS-1.1 through TS-1.7)
3. **Immutable audit log** (TS-5.1) — must exist before production data flows

### Phase 2: Core Pipeline

4. **Document parsing** (TS-2.1 through TS-2.6)
2. **Three-store writes** (TS-4.3)
3. **Provenance chain** (TS-5.2, TS-5.3)

### Phase 3: Governance + Transparency (the differentiator)

7. **PII detection and redaction** (TS-3.1, TS-3.2)
2. **Document classification** (TS-3.3)
3. **Vendor Acceptance Report** (D-1.1) — highest-ROI differentiator; solves Dana's core pain point
4. **Injection defense** (TS-6.1)

### Phase 4: Retrieval and Serving

11. **RAG retrieval with retrieval proofs** (D-1.3)
2. **Idempotent delta processing** (D-4.1)
3. **Pipeline job status tracking** (TS-7.1, TS-7.2)

### Defer to Post-MVP

- **D-2.1 Offline Docker bundle**: High complexity, parallel workstream. Build after online pipeline is proven. But architect for it from day one (no hard dependencies on external APIs in core pipeline logic).
- **D-1.2 Parse preview with diff**: Valuable but requires frontend investment. Acceptance report (D-1.1) covers 80% of the need.
- **D-3.3 Automated compliance evidence**: High value but requires mature audit log first. Build after several months of production audit data.
- **D-4.3 Schema evolution**: Important for long-term maintenance but not needed at launch if schema is designed carefully from the start.
- **D-1.4 Self-service dashboard**: Acceptance reports via email/API cover initial needs. Dashboard is a Q2+ investment.
- **D-5.1 Sandbox tenant**: Can use a regular tenant with ephemeral flag initially. Purpose-built sandbox is a refinement.

---

## Sources and Confidence Notes

| Area | Confidence | Basis |
|------|------------|-------|
| Intake/ingestion features | HIGH | Well-established patterns across enterprise ETL platforms; confirmed by project artifacts (ETL_PIPELINE_PROPOSAL.md, THREAT_MODEL_SAFETY.md) |
| Document parsing features | HIGH | Docling and Unstructured capabilities well-documented in training data; confirmed by project notebooks |
| Data governance (PII/redaction) | MEDIUM | Presidio, spaCy NER well-known; specific regulated industry requirements based on training knowledge of HIPAA/GDPR, not verified against current compliance checklists |
| Multi-tenant isolation patterns | HIGH | Per-tenant storage/network/key isolation is well-established enterprise architecture; confirmed by project artifacts |
| Audit and compliance features | HIGH | Immutable audit logs, provenance chains are standard in regulated industries; confirmed by THREAT_MODEL_SAFETY.md |
| Injection defense | HIGH | Document injection is a well-documented threat vector for RAG systems; confirmed by project's THREAT_MODEL_SAFETY.md |
| Offline/air-gapped operation | MEDIUM | Architectural pattern is sound; specific Nomic embed-text offline capabilities and ClamAV offline signature management based on training knowledge |
| Anti-features | HIGH | Based on extensive patterns of enterprise ETL mistakes observed across training data; cross-validated against project's explicit exclusions |
| Competitive landscape | LOW | Web research tools unavailable; competitor feature comparisons based on training knowledge, not current product pages. Competitors referenced implicitly: Unstructured Platform, LlamaIndex Enterprise, Haystack, Scale AI, Reducto, LlamaCloud |

**Research limitation:** WebSearch, WebFetch, and Context7 tools were unavailable during this research session. All findings are based on training knowledge (cutoff: May 2025) cross-referenced against the project's existing artifacts. Feature claims about specific tools (Docling, Unstructured, Qdrant, Nomic) should be validated against current documentation before locking into implementation plans.
