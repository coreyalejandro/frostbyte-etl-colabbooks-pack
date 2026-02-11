# Architecture Patterns

**Domain:** Multi-tenant document ETL pipelines for regulated industries
**Researched:** 2026-02-08
**Overall confidence:** MEDIUM (external verification tools unavailable; findings based on training data cross-referenced with project artifacts)

## Recommended Architecture

The Frostbyte multi-tenant document ETL pipeline follows a **control plane / data plane separation** pattern with **per-tenant isolated data planes** provisioned on Hetzner Cloud. This is the dominant pattern for regulated multi-tenant systems where tenant isolation must be provable by construction, not policy.

The architecture has three tiers:

1. **Control Plane** -- single, shared, manages tenant lifecycle, routing, audit aggregation
2. **Data Plane (per-tenant)** -- isolated compute, storage, and networking per tenant
3. **Audit Plane** -- append-only, immutable, write-once log store shared across tenants but write-only from each

```
                    +---------------------------+
                    |      CONTROL PLANE        |
                    |  (shared, multi-tenant)    |
                    |                           |
                    |  Tenant Registry          |
                    |  Provisioning Orchestrator|
                    |  API Gateway / Auth       |
                    |  Job Dispatcher           |
                    |  Audit Stream Aggregator  |
                    +-----+----------+----------+
                          |          |
              +-----------+          +-----------+
              |                                  |
    +---------v---------+           +-----------v---------+
    |   DATA PLANE      |           |   DATA PLANE        |
    |   Tenant A        |           |   Tenant B          |
    |                   |           |                     |
    |  Intake Gateway   |           |  Intake Gateway     |
    |  Parse Workers    |           |  Parse Workers      |
    |  Policy Engine    |           |  Policy Engine      |
    |  Object Store     |           |  Object Store       |
    |  Relational DB    |           |  Relational DB      |
    |  Vector Store     |           |  Vector Store       |
    |  Embedding Svc    |           |  Embedding Svc      |
    |  RAG Serving API  |           |  RAG Serving API    |
    +---------+---------+           +-----------+---------+
              |                                  |
              +----------------+-----------------+
                               |
                    +----------v----------+
                    |    AUDIT PLANE      |
                    |  (append-only)      |
                    |                     |
                    |  Immutable Log DB   |
                    |  Event Stream       |
                    +---------------------+
```

### Why This Architecture

**Control plane / data plane separation** is the standard for regulated multi-tenant SaaS because:

- The control plane never touches tenant data. It manages lifecycle, routing, and metering. This means a compromise of the control plane does not expose document content.
- Each data plane is a self-contained environment. Blast radius is limited to one tenant by construction.
- The audit plane is write-only from data planes, read-only from operations. This prevents tampering.
- Online and offline modes map cleanly: online mode uses the full three-tier topology; offline mode collapses the data plane into a Docker Compose bundle with the control plane replaced by static configuration.

**Confidence: MEDIUM** -- This pattern is well-established in enterprise SaaS (AWS multi-account, GCP per-project, Azure landing zones). Applying it to Hetzner requires manual implementation since Hetzner has no native multi-tenancy abstraction like AWS Organizations. The project artifacts already describe this pattern in `diagrams/tenancy.mmd`.

---

## Component Boundaries

### Control Plane Components

| Component | Responsibility | Communicates With | Trust Level |
|-----------|---------------|-------------------|-------------|
| **API Gateway** | External-facing entry point. TLS termination, rate limiting, JWT validation, tenant routing | Tenant Registry, Job Dispatcher, Data Plane Intake Gateways | HIGH -- validates all inbound requests |
| **Tenant Registry** | Stores tenant metadata, provisioning state, configuration, feature flags, API keys | Provisioning Orchestrator, API Gateway, Audit Aggregator | HIGH -- source of truth for tenant identity |
| **Provisioning Orchestrator** | Creates/destroys per-tenant infrastructure via Hetzner Cloud API (servers, networks, firewalls, volumes) | Hetzner Cloud API, Tenant Registry, DNS/certs | HIGH -- infrastructure-level access |
| **Job Dispatcher** | Routes ingestion jobs to the correct tenant data plane. Tracks job state for observability | API Gateway, Data Plane Task Queues, Tenant Registry | MEDIUM -- does not touch document content |
| **Audit Stream Aggregator** | Collects audit events from all tenant data planes, writes to immutable audit store | Data Plane Audit Emitters, Immutable Audit DB | HIGH -- must guarantee append-only semantics |

### Data Plane Components (per-tenant)

| Component | Responsibility | Communicates With | Trust Level |
|-----------|---------------|-------------------|-------------|
| **Intake Gateway** | Trust boundary. Authenticates vendor uploads, validates manifests, checksums, scans files, generates intake receipts | API Gateway (via control plane routing), Object Store, Task Queue | CRITICAL -- first contact with untrusted documents |
| **Task Queue (Celery/Redis)** | Manages job lifecycle for parse, enrich, embed, index steps. Handles retries, dead-letter, idempotency | Intake Gateway, Parse Workers, Policy Engine, Embedding Service | MEDIUM -- orchestration, no data access |
| **Parse Workers** | Run Docling + Unstructured to convert documents to canonical structured JSON | Task Queue, Object Store (read raw, write normalized) | MEDIUM -- processes untrusted content in sandbox |
| **Policy Engine** | PII detection, document classification, injection defense, deterministic chunking | Task Queue, Object Store (read normalized), Relational DB (write metadata) | HIGH -- safety-critical gate |
| **Embedding Service** | Generates vector embeddings. Online: OpenRouter API. Offline: Nomic embed-text local model | Task Queue, Vector Store (write), Policy Engine (read chunks) | MEDIUM -- model version must be recorded |
| **Object Store (MinIO/S3-compat)** | Stores raw uploads and normalized artifacts. Per-tenant bucket with tenant-scoped credentials | Intake Gateway, Parse Workers, Policy Engine, Serving API | HIGH -- contains actual document content |
| **Relational DB (PostgreSQL)** | Governance metadata, lineage, job state, retention rules, chunk-to-source mappings | Policy Engine, Serving API, Audit Emitter | HIGH -- schema isolation per tenant |
| **Vector Store (Qdrant)** | Stores embeddings for RAG retrieval. Per-tenant collection or per-tenant instance | Embedding Service, Serving API | MEDIUM -- derived data, rebuildable from source |
| **RAG Serving API** | Retrieval endpoint. Returns source slices with provenance. Enforces cite-only-from-retrieval | Vector Store, Relational DB, Object Store, Audit Emitter | HIGH -- external-facing, must enforce retrieval proof |
| **Audit Emitter** | Emits structured events for every pipeline step to the Audit Plane | All data plane components (receives events), Audit Stream Aggregator | HIGH -- integrity of audit chain |

---

## Data Flow

### Online Mode -- Full Pipeline

```
VENDOR                 CONTROL PLANE              DATA PLANE (Tenant X)           AUDIT PLANE
  |                         |                            |                            |
  |-- Upload batch -------->|                            |                            |
  |   (HTTPS + manifest)    |                            |                            |
  |                         |-- Validate JWT ----------->|                            |
  |                         |-- Route to tenant -------->|                            |
  |                         |                            |                            |
  |                         |                    [1] INTAKE GATEWAY                   |
  |                         |                     - Verify manifest                   |
  |                         |                     - Checksum each file                |
  |                         |                     - MIME allowlist check              |
  |                         |                     - Malware scan (ClamAV)             |
  |                         |                     - Write raw to Object Store         |
  |                         |                     - Generate intake receipt           |
  |                         |                     - Emit audit event ----------------->|
  |                         |                     - Enqueue parse jobs                |
  |                         |                            |                            |
  |                         |                    [2] PARSE WORKERS                    |
  |                         |                     - Read raw from Object Store        |
  |                         |                     - Docling: layout-aware conversion  |
  |                         |                     - Unstructured: partition + chunk    |
  |                         |                     - Write canonical JSON to ObjStore  |
  |                         |                     - Emit audit event ----------------->|
  |                         |                     - Enqueue policy check              |
  |                         |                            |                            |
  |                         |                    [3] POLICY ENGINE                    |
  |                         |                     - PII/PHI scan + redact             |
  |                         |                     - Document classification           |
  |                         |                     - Injection defense scan            |
  |                         |                     - Deterministic chunk IDs           |
  |                         |                     - Write metadata to Relational DB   |
  |                         |                     - Emit audit event ----------------->|
  |                         |                     - Enqueue embedding job             |
  |                         |                            |                            |
  |                         |                    [4] EMBEDDING SERVICE                |
  |                         |                     - Read chunks from Object Store     |
  |                         |                     - Call OpenRouter embeddings API    |
  |                         |                     - Record model + version            |
  |                         |                     - Write vectors to Qdrant           |
  |                         |                     - Write index metadata to PG        |
  |                         |                     - Emit audit event ----------------->|
  |                         |                            |                            |
  |                         |                    [5] SERVING (on query)               |
  |                         |                     - Receive RAG query                 |
  |                         |                     - Retrieve from Qdrant              |
  |                         |                     - Fetch source slices from ObjStore |
  |                         |                     - Build retrieval proof object      |
  |                         |                     - Return answer + provenance        |
  |                         |                     - Emit audit event ----------------->|
  |                         |                            |                            |
```

### Data Transformation Chain

```
Raw Document (PDF/DOCX/etc)
    |
    v
Intake Receipt JSON
  { tenant_id, file_id, sha256, timestamp, source, mime_type, scan_result }
    |
    v
Canonical Structured Document JSON
  { doc_id, file_id, sections[], tables[], figures[],
    reading_order[], offsets[], lineage: { raw_ref, parse_version } }
    |
    v
Policy-Enriched Chunks
  { chunk_id (deterministic), doc_id, text, metadata,
    pii_scan_result, classification, injection_score,
    offsets: { page, start_char, end_char } }
    |
    v
Embedded Chunks (stored in three places)
  Object Store:  raw + normalized artifacts (immutable)
  Relational DB: chunk metadata, lineage, job state
  Vector Store:  embedding vector + chunk_id + metadata filter fields
```

### Offline Mode -- Collapsed Data Plane

In offline mode, the three-tier architecture collapses into a single Docker Compose stack running on an air-gapped host:

```
AIR-GAPPED HOST
  |
  +-- Docker Compose
       |
       +-- intake-gateway      (same code, static tenant config)
       +-- parse-worker        (Docling + Unstructured containers)
       +-- policy-engine       (same rules, local execution)
       +-- embedding-service   (Nomic embed-text, no outbound)
       +-- redis               (task queue broker)
       +-- celery-worker       (job orchestration)
       +-- postgres            (relational DB, single tenant)
       +-- qdrant              (vector store, single tenant)
       +-- minio               (object store, single tenant)
       +-- validation-ui       (receipts, diffs, export)
       +-- audit-logger        (writes to local append-only file/DB)
       |
       +-- NETWORK: internal only, no outbound routes
       |
       +-- VOLUMES:
            /data/raw           (uploaded documents)
            /data/normalized    (structured JSON)
            /data/vectors       (qdrant persistence)
            /data/db            (postgres persistence)
            /data/audit         (append-only audit log)
            /data/export        (signed export bundles)
```

**Key differences from online mode:**

| Concern | Online Mode | Offline Mode |
|---------|-------------|--------------|
| Tenant provisioning | Hetzner Cloud API, dynamic | Static config in docker-compose.yml |
| Networking | Per-tenant firewall rules | `internal: true`, no outbound routes |
| Embeddings | OpenRouter API | Nomic embed-text local container |
| Audit stream | Aggregated to central audit plane | Local append-only file/SQLite |
| Export | N/A (data stays in cloud) | Signed bundle: JSON + index snapshot + audit log |
| Updates | Rolling deploys via orchestrator | New Docker image versions, shipped as tarballs |

---

## Per-Tenant Provisioning Pattern (Hetzner Cloud)

Each tenant gets a fully isolated environment provisioned via the Hetzner Cloud API. Hetzner does not have a native multi-tenancy construct (unlike AWS Organizations), so isolation must be constructed explicitly.

**Confidence: MEDIUM** -- Based on training data about Hetzner Cloud API capabilities. Hetzner provides Projects as an isolation boundary but their API surface is simpler than hyperscaler equivalents. Verify exact API endpoints against current Hetzner docs.

### Provisioning Sequence

```
1. Control Plane receives "create tenant" request
    |
2. Create Hetzner Cloud Project (or use API tokens scoped per tenant)
    |
3. Provision compute:
    - Create server(s) for parse workers, API, etc.
    - Apply labels: tenant_id, environment, role
    |
4. Provision networking:
    - Create private network (10.x.tenant_id.0/24)
    - Create firewall rules:
      - Allow inbound HTTPS from API gateway only
      - Allow internal traffic within tenant network
      - DENY all cross-tenant traffic
      - DENY outbound (except OpenRouter API if online mode)
    |
5. Provision storage:
    - Create volume(s) for persistent data
    - Deploy MinIO with tenant-scoped bucket + credentials
    - Deploy PostgreSQL with tenant-scoped database + user
    - Deploy Qdrant with tenant-scoped collection
    |
6. Provision secrets:
    - Generate tenant API keys
    - Generate tenant DB credentials
    - Generate tenant object store credentials
    - Store all in control plane secret manager (Vault or similar)
    |
7. Configure DNS:
    - tenant-id.pipeline.frostbyte.io -> tenant API endpoint
    |
8. Register in Tenant Registry:
    - Record provisioning state, endpoints, health check URLs
    |
9. Emit audit event: TENANT_PROVISIONED
```

### Tenant Isolation Evidence

Every tenant isolation claim must be backed by verifiable evidence:

| Isolation Layer | Mechanism | Evidence |
|----------------|-----------|----------|
| Compute | Separate Hetzner servers per tenant | Server list filtered by tenant label |
| Network | Hetzner private network + firewall | Firewall rule export, network topology |
| Object storage | Per-tenant MinIO bucket, separate credentials | Bucket policy, credential scope |
| Relational DB | Per-tenant PostgreSQL database, separate user | `pg_hba.conf` rules, role grants |
| Vector store | Per-tenant Qdrant collection (or instance) | Collection list, API key scope |
| Encryption | Per-tenant encryption keys | Key policy, key-to-tenant mapping |
| Audit | Write-only from tenant, no cross-read | Audit log ACLs |

---

## Intake Gateway Design (Trust Boundary)

The intake gateway is the most critical security boundary in the system. Every document entering the pipeline passes through it. It is the first line of defense against malicious content.

### Request Flow

```
Vendor Request
    |
    v
[TLS Termination]
    |
    v
[JWT Validation] -- extract tenant_id from token claims
    |
    v
[Rate Limiter] -- per-tenant quota enforcement
    |
    v
[Manifest Validation]
  - Parse manifest (JSON/CSV)
  - Verify expected file count
  - Verify no duplicate file IDs
    |
    v
[Per-File Processing Loop]
  |
  +-- [MIME Type Check] -- allowlist: PDF, DOCX, XLSX, TXT, CSV, PNG, TIFF
  |     |
  |     +-- REJECT if not on allowlist
  |
  +-- [Size Check] -- reject if > configured max (e.g., 500MB)
  |
  +-- [Checksum Verification] -- compute SHA-256, compare with manifest
  |     |
  |     +-- REJECT if mismatch
  |
  +-- [Malware Scan] -- ClamAV or similar
  |     |
  |     +-- QUARANTINE if flagged
  |
  +-- [Write to Object Store] -- raw/{tenant_id}/{file_id}/{sha256}
  |
  +-- [Generate Intake Receipt]
  |     { tenant_id, file_id, sha256, timestamp, source,
  |       mime_type, size_bytes, scan_result, manifest_ref }
  |
  +-- [Emit Audit Event] -- DOCUMENT_INGESTED
  |
  +-- [Enqueue Parse Job] -- to tenant task queue
    |
    v
[Return Batch Receipt]
  { batch_id, file_count, accepted, rejected, quarantined }
```

---

## Document Processing Pipeline

### Docling + Unstructured Orchestration

Docling and Unstructured serve complementary roles. Use both, in sequence, for maximum extraction coverage.

**Confidence: MEDIUM** -- Based on training data about both libraries. Docling excels at layout-aware PDF conversion (tables, figures, reading order). Unstructured excels at partitioning and chunking with metadata. The combination is additive, not redundant.

```
Raw Document
    |
    v
[DOCLING STAGE]
  Purpose: Layout-aware document conversion
  - PDF -> structured representation with tables, figures, sections
  - DOCX -> structured representation
  - Preserves reading order
  - Extracts table structures as data frames
  - Records page/position offsets
  Output: DoclingDocument object (intermediate)
    |
    v
[UNSTRUCTURED STAGE]
  Purpose: Partitioning, chunking, metadata enrichment
  - Partition the Docling output into elements
  - Apply chunking strategy (by_title, by_page, or fixed)
  - Enrich with element-level metadata
  - Generate stable chunk IDs: hash(doc_id + page + start_offset + end_offset)
  Output: List of Element objects with metadata
    |
    v
[CANONICAL JSON ASSEMBLY]
  Purpose: Create the pipeline's internal document format
  - Merge Docling structure info + Unstructured elements
  - Assign deterministic chunk IDs
  - Record lineage: { raw_sha256, docling_version, unstructured_version }
  - Write to Object Store as normalized/{tenant_id}/{doc_id}/structured.json
```

### Why Two Tools

| Capability | Docling | Unstructured | Together |
|-----------|---------|-------------|---------|
| PDF table extraction | Excellent (layout model) | Good (heuristic) | Use Docling result |
| Reading order | Excellent | Limited | Use Docling result |
| Chunking strategies | Limited | Excellent (multiple) | Use Unstructured |
| Metadata enrichment | Basic | Rich (element types) | Use Unstructured |
| OCR fallback | Good | Good | Either, based on quality |
| Document format coverage | PDF, DOCX, PPTX, images | PDF, DOCX, XLSX, HTML, TXT, images, email | Union of both |

---

## Policy Gate Patterns

Policy gates are synchronous checkpoints in the pipeline. A document cannot proceed past a gate without passing all checks. Failed gates quarantine the document and emit an audit event.

### Gate 1: PII/PHI Detection

```
Input: Canonical structured document chunks
    |
    v
[NER-based PII Scanner]
  - Named entity recognition for: names, SSNs, emails, phone numbers,
    addresses, dates of birth, medical record numbers
  - Configurable per-tenant: which PII types to flag vs. redact vs. pass
    |
    v
[Action based on tenant policy]
  - REDACT: replace PII span with [REDACTED:TYPE]
  - FLAG: mark chunk metadata, allow through
  - BLOCK: quarantine entire document
    |
    v
[Record in metadata]
  - pii_types_found, pii_action_taken, redacted_spans[]
```

### Gate 2: Document Classification

```
Input: Canonical structured document
    |
    v
[Classifier]
  - Rule-based first: filename patterns, header keywords, metadata fields
  - ML-assisted second: zero-shot or few-shot classification
  - Categories: contract, invoice, SOP, policy, correspondence, legal_filing, other
    |
    v
[Human-in-loop gate (optional)]
  - If confidence < threshold, route to review queue
  - Dana (vendor ops) approves or corrects classification
    |
    v
[Record in metadata]
  - classification, confidence_score, classifier_version, human_override
```

### Gate 3: Injection Defense

```
Input: Document text content (all chunks)
    |
    v
[Pattern Scanner]
  - Regex patterns for known injection phrases:
    "ignore previous instructions", "you are now", "system:", etc.
  - Homoglyph detection (Unicode lookalikes hiding instructions)
  - Invisible character detection (zero-width chars, RTL overrides)
    |
    v
[Heuristic Scorer]
  - Score each chunk for injection likelihood (0.0 - 1.0)
  - Factors: pattern matches, unusual character distributions,
    instruction-like sentence structures
    |
    v
[Action based on score]
  - score < 0.3: PASS
  - score 0.3-0.7: FLAG for review, allow through with warning
  - score > 0.7: QUARANTINE, do not embed, do not serve
    |
    v
[Record in metadata]
  - injection_score, patterns_matched[], action_taken
```

**Critical architectural decision:** Injection defense happens BEFORE embedding. Malicious content must never reach the vector store where it could influence retrieval results.

---

## Storage Architecture

### Three-Store Pattern

Every tenant has three isolated stores. This is not optional -- the separation exists because each store serves a different access pattern and retention policy.

```
+------------------+     +------------------+     +------------------+
|   OBJECT STORE   |     |  RELATIONAL DB   |     |  VECTOR STORE    |
|   (MinIO)        |     |  (PostgreSQL)    |     |  (Qdrant)        |
|                  |     |                  |     |                  |
| raw/{file_id}/   |     | documents        |     | collection:      |
|   original file  |     | chunks           |     |   tenant_{id}    |
|                  |     | lineage          |     |                  |
| normalized/      |     | jobs             |     | vectors:         |
|   {doc_id}/      |     | audit_events     |     |   chunk_id       |
|   structured.json|     | classifications  |     |   embedding      |
|                  |     | pii_findings     |     |   metadata:      |
| export/          |     | tenant_config    |     |     doc_id       |
|   bundles/       |     | retention_rules  |     |     page         |
|                  |     |                  |     |     classification|
+------------------+     +------------------+     +------------------+
   |                        |                        |
   | Immutable blobs        | Queryable metadata     | Similarity search
   | Retention: configurable| Retention: long        | Retention: rebuildable
   | Backup: snapshots      | Backup: pg_dump        | Backup: rebuild from source
```

### Why Three Stores

| Store | Purpose | Why Separate |
|-------|---------|-------------|
| Object Store | Immutable document artifacts | Blob storage optimized for large files; retention policies differ from metadata; source of truth for reprocessing |
| Relational DB | Governance metadata, lineage, state | Needs ACID transactions, complex queries, joins between entities; powers the acceptance report |
| Vector Store | Embeddings for semantic retrieval | Needs ANN index, similarity search; rebuild from source if needed; different scaling characteristics |

### Per-Tenant Isolation Strategy by Store

| Store | Isolation Method | Credential Scope |
|-------|-----------------|-----------------|
| MinIO | Separate bucket per tenant with bucket policy | Per-tenant access key + secret key |
| PostgreSQL | Separate database per tenant with dedicated user | Per-tenant user, `pg_hba.conf` restricted |
| Qdrant | Separate collection per tenant (shared instance) or separate instance (maximum isolation) | Per-tenant API key with collection-scoped access |

**Recommendation:** Start with collection-per-tenant in Qdrant (simpler ops) and separate-database-per-tenant in PostgreSQL (strong isolation). Move to separate Qdrant instances only if a tenant requires it contractually or if collection-level isolation proves insufficient for compliance audits.

**Confidence: MEDIUM** -- Qdrant supports multi-tenancy via payload-based filtering or separate collections. Separate collections provide stronger isolation boundaries. Verify current Qdrant multi-tenancy docs for latest recommendations.

---

## Serving Layer (RAG API with Provenance)

### Retrieval Flow

```
Query Request
  { tenant_id, query_text, top_k, filters }
    |
    v
[Authenticate + authorize] -- JWT validation, tenant scope check
    |
    v
[Embed query] -- same model used for indexing (version must match)
    |
    v
[Vector search] -- Qdrant, collection: tenant_{id}
  - ANN search with metadata filters (classification, date range, etc.)
  - Return top_k chunk_ids with similarity scores
    |
    v
[Fetch source slices] -- Object Store + Relational DB
  - For each chunk_id:
    - Fetch text from Object Store (or cached in PG)
    - Fetch metadata: doc_id, page, start_char, end_char, classification
    - Fetch lineage: parse_version, embed_model, embed_version
    |
    v
[Build retrieval proof]
  {
    query_id,
    chunks: [
      {
        chunk_id, doc_id, text, page, offsets,
        similarity_score, embed_model, embed_version,
        source_sha256
      }
    ],
    timestamp,
    tenant_id
  }
    |
    v
[Return response]
  { answer (if generation enabled), retrieval_proof, metadata }
    |
    v
[Emit audit event] -- RETRIEVAL_EXECUTED
  { query_id, tenant_id, chunks_returned, timestamp }
```

### Cite-Only-From-Retrieval Enforcement

The serving layer MUST enforce that any generated answer is grounded in the returned chunks. This is a hard architectural constraint, not a prompt engineering suggestion.

- Every claim in the answer must reference a chunk_id from the retrieval proof
- If the model generates text not backed by a chunk, flag or suppress
- Retrieval proof object is stored alongside the answer for audit purposes

---

## Audit Stream Architecture

### Design Principles

1. **Append-only**: Events can only be written, never updated or deleted
2. **Immutable**: Once written, the event record cannot be modified
3. **Complete**: Every pipeline step emits an event
4. **Tenant-attributed**: Every event includes tenant_id
5. **Timestamped**: Server-side timestamps, not client-side

### Event Schema

```json
{
  "event_id": "uuid-v7 (time-ordered)",
  "tenant_id": "tenant_abc",
  "event_type": "DOCUMENT_INGESTED | DOCUMENT_PARSED | POLICY_GATE_PASSED | POLICY_GATE_FAILED | DOCUMENT_EMBEDDED | INDEX_WRITTEN | RETRIEVAL_EXECUTED | TENANT_PROVISIONED | TENANT_DEPROVISIONED",
  "timestamp": "2026-02-08T12:00:00Z",
  "actor": "system | user_id",
  "resource_id": "file_id | doc_id | chunk_id | query_id",
  "resource_type": "document | chunk | query | tenant",
  "details": {
    "pipeline_version": "1.2.0",
    "component": "intake-gateway | parse-worker | policy-engine | embedding-service | serving-api",
    "input_hash": "sha256 of input",
    "output_hash": "sha256 of output",
    "model_version": "nomic-embed-text-v1 | openrouter/model-name",
    "duration_ms": 1234,
    "status": "success | failure | quarantined"
  },
  "previous_event_id": "uuid of preceding event in chain (for lineage)"
}
```

### Implementation

**Online mode:**

- Each data plane component emits events to a local Redis stream (or Kafka topic if scale warrants)
- Audit Stream Aggregator in control plane consumes from all tenant streams
- Writes to append-only PostgreSQL table with `INSERT`-only grants (no `UPDATE`, no `DELETE`)
- Alternatively: append-only log file with periodic rotation and signing

**Offline mode:**

- Events written to local append-only SQLite database
- Exported as part of the signed bundle
- File-level integrity: SHA-256 of audit log included in export manifest

**Confidence: MEDIUM** -- Append-only PostgreSQL with restricted grants is a proven pattern. For higher assurance, consider write-once storage (S3 Object Lock, or WORM-compliant storage). This is an implementation decision, not an architectural one.

---

## Offline Bundle Architecture

### Bundle Contents

```
frostbyte-etl-offline-v{version}.tar.gz
  |
  +-- docker-compose.yml           # Full stack definition
  +-- .env.example                  # Configuration template
  +-- images/                       # Pre-built Docker images
  |     +-- intake-gateway.tar
  |     +-- parse-worker.tar
  |     +-- policy-engine.tar
  |     +-- embedding-service.tar
  |     +-- celery-worker.tar
  |     +-- validation-ui.tar
  +-- models/                       # Pre-downloaded ML models
  |     +-- nomic-embed-text-v1/    # Local embedding model weights
  |     +-- pii-ner-model/          # PII detection model (if ML-based)
  +-- config/                       # Default configurations
  |     +-- allowlist.json          # Permitted MIME types
  |     +-- policy-rules.json       # PII/classification/injection rules
  |     +-- clamav-db/              # Malware signatures (offline update)
  +-- scripts/
  |     +-- install.sh              # Load images, create volumes, verify
  |     +-- verify.sh               # Health checks for all services
  |     +-- export.sh               # Generate signed export bundle
  +-- MANIFEST.json                 # Bundle manifest with SHA-256 of every file
  +-- COMPATIBILITY.md              # Hardware/OS/GPU requirements
```

### Network Isolation

```yaml
# docker-compose.yml network configuration
networks:
  etl-internal:
    driver: bridge
    internal: true    # <-- KEY: no outbound connectivity
```

All services bind to `etl-internal` network only. No service has a port mapped to the host except the validation UI (mapped to localhost only).

### Offline Update Cycle

```
1. Frostbyte builds new bundle version on CI
2. Bundle is signed (GPG or cosign)
3. Bundle shipped to customer (secure transfer, USB, etc.)
4. Customer runs install.sh:
   a. Verify bundle signature
   b. Load new Docker images
   c. Run database migrations
   d. Verify health checks
5. Zero-downtime cutover (stop old, start new)
```

---

## API Gateway and Service Mesh Patterns

### API Gateway (Control Plane)

**Recommendation:** Use a lightweight reverse proxy (Traefik or Caddy) rather than a heavy API gateway (Kong, AWS API Gateway). Reason: Hetzner environment is self-managed, and the gateway needs are straightforward -- TLS, routing, rate limiting, JWT validation.

```
Internet --> [Traefik/Caddy]
                |
                +-- /api/v1/tenants/*      --> Tenant Registry service
                +-- /api/v1/ingest/*       --> routes to tenant-specific Intake Gateway
                +-- /api/v1/query/*        --> routes to tenant-specific Serving API
                +-- /api/v1/admin/*        --> Control Plane admin endpoints
                +-- /api/v1/audit/*        --> Audit read endpoints (operations only)
```

### Internal Communication

**Recommendation:** Direct HTTP between services within a tenant's data plane. No service mesh needed at initial scale. Add mTLS between services if compliance requires encrypted internal traffic.

Rationale: Service meshes (Istio, Linkerd) add operational complexity. For a system with 5-20 tenants, direct service-to-service communication with application-level auth tokens is sufficient. Revisit at 50+ tenants or when compliance demands mutual TLS on all internal traffic.

**Confidence: LOW** -- This is a pragmatic recommendation. If Frostbyte's compliance requirements mandate mTLS on all internal traffic from day one, a service mesh becomes necessary. Clarify with Frode.

---

## Job Orchestration

### Task Queue Architecture

**Recommendation:** Celery with Redis as broker. Reason: Python ecosystem standard, well-understood, supports task chains, retries, and dead-letter queues. The pipeline is batch-oriented (not streaming), making Celery appropriate.

```
[Intake Gateway]
    |
    v
[Redis Broker] -- per-tenant queue namespace: tenant_{id}.parse
    |
    v
[Celery Worker: parse]
    |-- success --> enqueue: tenant_{id}.policy
    |-- failure --> retry (max 3) --> dead-letter: tenant_{id}.dlq
    v
[Celery Worker: policy]
    |-- pass --> enqueue: tenant_{id}.embed
    |-- fail --> quarantine, emit audit event
    v
[Celery Worker: embed]
    |-- success --> enqueue: tenant_{id}.index
    |-- failure --> retry (max 3) --> dead-letter: tenant_{id}.dlq
    v
[Celery Worker: index]
    |-- success --> mark job complete, emit audit event
    |-- failure --> retry (max 3) --> dead-letter: tenant_{id}.dlq
```

### Idempotency

Every task must be idempotent. If a task is retried, the result must be identical to the first execution.

Implementation patterns:

- **Parse**: Deterministic output for same input. Use file SHA-256 as cache key. Skip if normalized output already exists with matching hash.
- **Policy**: Deterministic for same input + same policy version. Policy version recorded in metadata.
- **Embed**: Use chunk content hash + model version as cache key. Skip if vector already exists.
- **Index**: Upsert semantics (insert or update, never duplicate).

### Retry Policy

| Task | Max Retries | Backoff | Dead Letter Action |
|------|-------------|---------|-------------------|
| Parse | 3 | Exponential (10s, 60s, 300s) | Alert ops, mark document as failed |
| Policy | 2 | Fixed (30s) | Quarantine document, alert ops |
| Embed | 3 | Exponential (10s, 60s, 300s) | Alert ops, mark chunks as unembedded |
| Index | 3 | Exponential (10s, 60s, 300s) | Alert ops, mark as unindexed |

---

## Patterns to Follow

### Pattern 1: Envelope Pattern for Untrusted Content

**What:** Never pass raw document content in the same data structure as system instructions or control metadata. Wrap content in an "envelope" that the system treats as opaque data, never as instructions.

**When:** Every time document content moves between pipeline stages.

**Why:** Prevents injection attacks where document content is accidentally interpreted as system commands.

```python
# CORRECT: Content in envelope, never in control path
envelope = {
    "metadata": {  # system-controlled, trusted
        "tenant_id": "abc",
        "doc_id": "123",
        "stage": "policy_check"
    },
    "content": {  # untrusted, opaque blob
        "text": raw_document_text,
        "source_hash": sha256_of_raw
    }
}

# WRONG: Content mixed with system data
message = {
    "tenant_id": "abc",
    "instruction": f"Process this document: {raw_document_text}"  # INJECTION RISK
}
```

### Pattern 2: Hash Chain for Lineage

**What:** Every transformation records the hash of its input and output. This creates a verifiable chain from raw document to served chunk.

**When:** Every pipeline stage transition.

```
raw_sha256 --> parse(raw) --> normalized_sha256 --> policy(normalized) -->
chunk_sha256 --> embed(chunk) --> vector_sha256
```

### Pattern 3: Tenant Context Propagation

**What:** Tenant ID is set at the gateway and propagated through every service call. No service should infer or look up tenant context -- it is always passed explicitly.

**When:** Every cross-service call.

```python
# Set at gateway
context = TenantContext(tenant_id="abc", request_id="req-123")

# Propagated via header
headers = {
    "X-Tenant-ID": context.tenant_id,
    "X-Request-ID": context.request_id
}

# Validated at every service boundary
def validate_tenant_context(request):
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        raise AuthorizationError("Missing tenant context")
    if tenant_id != expected_tenant_for_this_data_plane:
        raise AuthorizationError("Tenant context mismatch")
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Shared Database with Row-Level Isolation

**What:** Using a single database for all tenants and relying on `WHERE tenant_id = ?` for isolation.

**Why bad:** One query without the filter clause leaks all tenant data. A SQL injection in any query exposes every tenant. Compliance auditors will flag this as insufficient isolation for regulated data.

**Instead:** Separate database per tenant. The blast radius of any data leak is bounded to one tenant.

### Anti-Pattern 2: Embedding Untrusted Content Before Policy Gates

**What:** Running embeddings on document content before PII detection and injection defense.

**Why bad:** Malicious or sensitive content ends up in the vector store, where it influences retrieval results and may be returned to users. Removing vectors after the fact is error-prone.

**Instead:** Policy gates (PII, classification, injection defense) run BEFORE embedding. Only clean, approved chunks reach the vector store.

### Anti-Pattern 3: Mutable Audit Logs

**What:** Storing audit events in a table that allows UPDATE or DELETE operations.

**Why bad:** Auditors cannot trust the log if it can be retroactively modified. In regulated industries, mutable audit logs fail compliance requirements.

**Instead:** Append-only table with INSERT-only grants. Consider write-once storage for highest assurance.

### Anti-Pattern 4: Fat Control Plane

**What:** Running document processing in the control plane instead of in per-tenant data planes.

**Why bad:** The control plane handles all tenants. If document processing happens there, a bug or exploit in parsing could affect all tenants. Violates blast-radius isolation.

**Instead:** Control plane only manages routing, lifecycle, and audit aggregation. All document processing happens in the tenant's isolated data plane.

### Anti-Pattern 5: Optimistic Offline Networking

**What:** Relying on firewalls or host-level rules to prevent outbound traffic in offline mode, rather than Docker network configuration.

**Why bad:** Host-level rules can be misconfigured, and the customer may modify them. Defense must be structural.

**Instead:** `internal: true` on the Docker network. This is an application-level guarantee that containers cannot reach the internet, regardless of host configuration.

---

## Scalability Considerations

| Concern | 5 Tenants | 50 Tenants | 500 Tenants |
|---------|-----------|------------|-------------|
| **Provisioning** | Manual via scripts, Hetzner API | Automated via orchestrator, templated | Fully automated with approval workflow |
| **Compute** | Dedicated servers per tenant | Right-sized servers, some shared worker pools | Kubernetes with per-tenant namespaces |
| **Vector Store** | Collection-per-tenant, shared Qdrant | Collection-per-tenant, multiple Qdrant instances | Dedicated Qdrant instance per tenant |
| **Control Plane** | Single server | HA pair | Clustered with leader election |
| **Audit Store** | Single PostgreSQL | Partitioned by tenant, monthly rotation | Dedicated audit service, object storage backend |
| **Monitoring** | Prometheus + Grafana, single instance | Per-tenant dashboards, alerting | Centralized observability platform |

---

## Build Order (Dependency Graph)

Components must be built in dependency order. Each layer depends on the layers below it.

```
LAYER 0: Foundation (no dependencies)
  [0a] Tenant data model + registry schema
  [0b] Audit event schema + append-only store
  [0c] Configuration framework (env vars, secrets)
  [0d] Docker Compose skeleton (networking, volumes)

LAYER 1: Storage (depends on Layer 0)
  [1a] Object Store setup (MinIO) -- per-tenant bucket provisioning
  [1b] Relational DB setup (PostgreSQL) -- per-tenant database provisioning
  [1c] Vector Store setup (Qdrant) -- per-tenant collection provisioning
  [1d] Redis setup -- task queue broker

LAYER 2: Intake (depends on Layer 0 + 1)
  [2a] Intake Gateway -- auth, manifest, checksum, scan, receipt
  [2b] Task Queue framework (Celery) -- job dispatch, retry, dead-letter

LAYER 3: Processing (depends on Layer 2)
  [3a] Parse Workers -- Docling + Unstructured integration
  [3b] Canonical JSON schema -- structured document format

LAYER 4: Policy (depends on Layer 3)
  [4a] PII detection + redaction
  [4b] Document classification
  [4c] Injection defense scoring

LAYER 5: Embedding (depends on Layer 4)
  [5a] Embedding service -- OpenRouter (online) + Nomic (offline)
  [5b] Vector index writes with model version recording

LAYER 6: Serving (depends on Layer 5)
  [6a] RAG retrieval API with provenance
  [6b] Retrieval proof object generation

LAYER 7: Operations (depends on all above)
  [7a] Provisioning orchestrator (Hetzner Cloud API)
  [7b] API Gateway (Traefik/Caddy) + tenant routing
  [7c] Monitoring + alerting (Prometheus/Grafana)
  [7d] Offline bundle packaging + signing

LAYER 8: Validation (depends on Layer 7)
  [8a] Vendor acceptance report generation
  [8b] Validation UI (receipts, diffs, export)
  [8c] End-to-end integration tests
```

### Critical Path

The critical path for a minimum demonstrable pipeline:

```
[0a] Tenant model --> [0c] Config --> [0d] Docker skeleton
                                          |
[1a] Object Store --> [1b] PostgreSQL --> [1d] Redis
                                          |
                      [2a] Intake Gateway --> [2b] Task Queue
                                                 |
                      [3a] Parse Workers --------+
                                                 |
                      [4c] Injection Defense ----+  (minimum policy gate)
                                                 |
                      [5a] Embedding Service ----+
                                                 |
                      [6a] RAG API --------------+
                                                 |
                      [0b] Audit Schema ---------+  (must be wired from start)
```

**Build order rationale:**

1. **Start with storage and audit** (Layers 0-1): Everything else writes to these. They must exist first. The audit schema must be wired from the very first pipeline step, not bolted on later.

2. **Build intake next** (Layer 2): The trust boundary must exist before any documents enter the system. This is the first thing a vendor interacts with.

3. **Processing pipeline** (Layers 3-5): Build in order because each stage feeds the next. Parse before policy before embed. Cannot embed what has not been parsed and approved.

4. **Serving last** (Layer 6): Retrieval requires indexed content. It is the last component in the data flow and the first component users interact with.

5. **Operations concurrent** (Layer 7): Provisioning, gateway, and monitoring can be built in parallel with the pipeline stages. They are operationally important but architecturally independent.

6. **Offline bundle after online works** (Layer 7d): The offline bundle is a packaging of the same components. Get them working online first, then package for offline.

---

## Deployment Topology

### Online Mode

```test
                    INTERNET
                       |
              [Hetzner Load Balancer]
                       |
              [API Gateway Server]
              (Traefik + Control Plane services)
              (Tenant Registry, Job Dispatcher,
               Audit Aggregator, Provisioning API)
                       |
         +-------------+-------------+
         |                           |
  [Tenant A Network]         [Tenant B Network]
  (Private, firewalled)      (Private, firewalled)
         |                           |
  +------+------+            +------+------+
  | Server(s)   |            | Server(s)   |
  | - Workers   |            | - Workers   |
  | - Services  |            | - Services  |
  | - MinIO     |            | - MinIO     |
  | - Postgres  |            | - Postgres  |
  | - Qdrant    |            | - Qdrant    |
  | - Redis     |            | - Redis     |
  +------+------+            +------+------+
         |                           |
         +-------------+-------------+
                       |
              [Audit Store Server]
              (Append-only PostgreSQL)
              (Accessed by control plane only)
```

### Offline Mode

```
  AIR-GAPPED HOST (single machine)
         |
  [Docker Compose]
         |
  +------+------+
  | All services |
  | on internal  |
  | network      |
  | (no outbound)|
  |              |
  | intake-gw    |
  | parse-worker |
  | policy-eng   |
  | embed-svc    |
  | celery       |
  | redis        |
  | postgres     |
  | qdrant       |
  | minio        |
  | validation-ui|
  | audit-logger |
  +------+------+
         |
  [Host filesystem volumes]
  /data/raw
  /data/normalized
  /data/vectors
  /data/db
  /data/audit
  /data/export
```

---

## Sources

- Project artifacts: `docs/ETL_PIPELINE_PROPOSAL.md`, `docs/THREAT_MODEL_SAFETY.md`, `docs/CUSTOMER_JOURNEY_MAP.md`, `diagrams/*.mmd`, `notebooks/05_multi_tenant_isolation_hetzner.ipynb` (primary source, HIGH confidence)
- Hetzner Cloud API documentation: <https://docs.hetzner.cloud/> (referenced but not fetched in this session -- MEDIUM confidence on specific API details)
- Qdrant multi-tenancy documentation: <https://qdrant.tech/documentation/guides/multiple-partitions/> (referenced but not fetched -- MEDIUM confidence)
- Docling documentation: <https://docling-project.github.io/docling/> (referenced but not fetched -- MEDIUM confidence)
- Unstructured documentation: <https://docs.unstructured.io/open-source/introduction/overview> (referenced but not fetched -- MEDIUM confidence)
- Architecture patterns (control plane/data plane separation, envelope pattern, hash chain lineage): Based on training data from AWS multi-account patterns, GCP per-project isolation, and enterprise SaaS architecture literature (MEDIUM confidence -- well-established patterns but not verified against 2026 sources)

### Verification Notes

External research tools (WebSearch, WebFetch, Context7) were unavailable during this research session. All findings are based on:

1. **Project artifacts** (HIGH confidence) -- the existing proposal, threat model, diagrams, and notebooks
2. **Training data** (MEDIUM confidence) -- established architecture patterns for multi-tenant regulated systems
3. **No live verification** was possible for specific library versions, API endpoints, or current best practices

**Recommendations for verification:**

- Verify Hetzner Cloud API supports Project-level isolation and per-project API tokens
- Verify Qdrant collection-level isolation semantics and API key scoping
- Verify Docling + Unstructured can be composed in the described sequence
- Verify Celery task chain patterns support the described retry/dead-letter behavior
- Verify MinIO bucket policy supports the described per-tenant credential scoping
