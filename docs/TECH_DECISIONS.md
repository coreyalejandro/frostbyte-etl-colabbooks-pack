# Technology Decisions: Frostbyte Multi-Tenant ETL Pipeline

**Document version:** 1.0
**Created:** 2026-02-08
**Requirement traceability:** TECH-01 (Section 1), TECH-02 (Section 2), TECH-03 (Section 3)

---

## Document Conventions

This document contains two types of decisions:

- **Locked-in (L):** Specified by the client (Frode / Frostbyte). These are non-negotiable and included for completeness. Marked with **(L)** in the decision table.
- **Selected (S):** Chosen from evaluated alternatives based on project requirements. Each includes a rationale and the rejected alternatives with reasons. Marked with **(S)** in the decision table.

All decisions in this document are **FINAL for v1.0**. There is no "consider" or "evaluate" language. Every component has exactly one technology choice. Future version upgrades follow the Version Pin Update Procedure in Section 5.

---

## Section 1: Component Decision Table (TECH-01)

### 1.1 Client-Specified Components (Locked-In)

| # | Component | Selected Technology | Version Pin | Rationale | Alternatives Rejected | Why Rejected |
|---|-----------|-------------------|-------------|-----------|----------------------|--------------|
| 1 | Primary language **(L)** | Python | >=3.12 | Client requirement. Python is the standard for ETL, ML, and data engineering workloads. >=3.12 provides performance improvements and modern typing support. | N/A | Client-specified |
| 2 | Infrastructure provider **(L)** | Hetzner Cloud | Current API | Client requirement. Per-tenant VM provisioning with private networking, firewalls, and volumes. Data sovereignty on European infrastructure. | AWS, GCP, Azure | Client-specified; hyperscalers violate the sovereignty posture for this use case |
| 3 | Document parsing (layout) **(L)** | Docling | >=2.70 | Client requirement. Layout-aware document conversion with excellent table extraction, reading order preservation, and page/position offset recording. | N/A | Client-specified |
| 4 | Document parsing (chunking) **(L)** | Unstructured (OSS) | >=0.16 | Client requirement. Partitioning, chunking, and metadata enrichment. Structure-aware chunking strategies (by_title, by_page). Pairs with Docling for layout + chunking coverage. | N/A | Client-specified |
| 5 | Online embeddings **(L)** | OpenRouter (text-embedding-3-small) | API v1, dimensions=768 | Client requirement. OpenAI-compatible embeddings API via OpenRouter. Configured with `dimensions=768` to align with offline mode for cross-mode vector compatibility. | N/A | Client-specified |
| 6 | Offline embeddings **(L)** | Nomic embed-text v1.5 | v1.5, 768d native | Client requirement. Local inference via GPT4All, supports CPU and GPU. Native 768-dimensional output matches online mode configuration. GGUF quantized versions available for resource-constrained environments. | Nomic embed-text v2 MoE | v2 local inference via Ollama announced as "coming soon" but not confirmed; v1.5 is production-ready for local inference today |
| 7 | Offline orchestration **(L)** | Docker Compose | >=2.29 | Client requirement (implied by air-gapped offline mode). Single-host orchestration with `internal: true` networking for structural guarantee of no outbound connectivity. | N/A | Client-specified |

### 1.2 Selected Components (With Rationale)

| # | Component | Selected Technology | Version Pin | Rationale | Alternatives Rejected | Why Rejected |
|---|-----------|-------------------|-------------|-----------|----------------------|--------------|
| 8 | API framework **(S)** | FastAPI | >=0.115 | Async-first HTTP framework with native OpenAPI spec generation and Pydantic v2 validation. De facto standard for Python async APIs, minimizing onboarding friction for engineers and AI agents. | Litestar | Smaller ecosystem, higher onboarding friction despite technical merit |
| | | | | | Django REST Framework | Sync-first model adds overhead for async I/O ETL workloads; batteries (admin, auth, sessions) are irrelevant |
| | | | | | Flask | No async support, no built-in validation, no OpenAPI generation |
| 9 | ASGI server **(S)** | Uvicorn | >=0.30 | Standard production ASGI server for FastAPI. Pairs with Gunicorn for multi-worker process management in production. | Hypercorn | Smaller ecosystem; Uvicorn is the FastAPI community standard |
| 10 | Data validation **(S)** | Pydantic | >=2.10 | Already a FastAPI dependency. Rust-backed core provides 5-50x validation speedup over v1. Used for all internal schemas: structured document JSON, intake receipts, audit events, API models. Floor raised to >=2.10 for Python 3.14 support (current release: 2.12.5). | Marshmallow | No FastAPI integration; separate serialization and validation libraries |
| | | | | | attrs + cattrs | Requires manual schema definition; Pydantic provides more out of the box |
| 11 | Relational database **(S)** | PostgreSQL | >=16 | Row-level security (RLS) for defense-in-depth tenant isolation. JSONB columns for semi-structured metadata. Mature backup, replication, and point-in-time recovery for audit compliance. The standard for regulated multi-tenant data workloads. | MySQL / MariaDB | No row-level security; weaker JSONB support; fewer compliance-relevant extensions |
| | | | | | CockroachDB | Over-engineered for per-tenant isolated instances; distributed SQL adds operational complexity with no benefit when each tenant has its own DB |
| | | | | | SQLite | Not suitable for concurrent multi-process access in online API mode |
| 12 | ORM **(S)** | SQLAlchemy | >=2.0.46 with `sqlalchemy[asyncio]` | SQLAlchemy 2.0's new-style query API is fully typed. Async support via asyncpg driver. Note: asyncio greenlet is no longer auto-installed; the `sqlalchemy[asyncio]` install target is required. | Raw SQL | Unmaintainable at scale; loses migration tooling |
| | | | | | Django ORM | Wrong framework; tied to Django's sync-first model |
| | | | | | Tortoise ORM | Smaller ecosystem; less mature migration tooling |
| 13 | Async PG driver **(S)** | asyncpg | >=0.29 | Fastest Python PostgreSQL driver. Native async with no wrapper overhead. Required for FastAPI's async request handlers to avoid blocking the event loop. | psycopg3 (async) | Acceptable alternative but asyncpg has better raw performance for high-throughput scenarios |
| 14 | Migrations **(S)** | Alembic | >=1.13 | Standard migration tool for SQLAlchemy. Deterministic, version-controlled schema changes required for audit compliance. | Django migrations | Wrong framework |
| | | | | | manual SQL scripts | No version tracking, no dependency resolution, error-prone |
| 15 | Vector store **(S)** | Qdrant | >=1.13 (server and client) | Purpose-built vector DB with native collection-level isolation (one collection per tenant). Supports gRPC and REST APIs, built-in snapshot/backup for compliance. Runs as a single Docker container for the offline bundle. Floor raised from >=1.12 to >=1.13 per verified releases. Note: Qdrant 1.16 introduces tiered multitenancy, but collection-per-tenant is the decision for isolation-by-construction (see Resolved Open Questions). | pgvector | Weaker at scale; less clean isolation model (schema-per-tenant in PostgreSQL vs. native collections) |
| | | | | | Weaviate | Heavier operationally; module system adds unnecessary abstraction when embeddings are handled externally |
| | | | | | ChromaDB | Not production-ready for multi-tenant regulated workloads |
| | | | | | Milvus | Over-engineered for per-tenant isolated deployments; designed for billions of vectors in shared clusters |
| 16 | Object storage **(S)** | MinIO | Latest self-hosted | S3-compatible API means all code uses boto3, making it portable to any S3-compatible store with zero code changes. Runs as a single Docker container for the offline bundle. Built-in bucket policies for per-tenant isolation, server-side encryption, versioning, and lifecycle policies. **CRITICAL NOTICE:** MinIO community edition entered maintenance mode in December 2025. No new features or enhancements will be accepted; security fixes are evaluated case-by-case. Decision: **continue with MinIO (Option A)**. The S3 API is stable and feature-complete for this use case. The codebase is mature. For a planning pack, this is the lowest-risk choice. Migration target: Garage (Rust, Apache 2.0, v2.0) if MinIO is abandoned entirely. All application code uses boto3, making migration zero-code-change. | Garage | Newer, less battle-tested in regulated environments; documented as migration target |
| | | | | | SeaweedFS | More mature than Garage but adds distributed complexity unnecessary for per-tenant instances |
| | | | | | Hetzner Object Storage | S3-compatible for online mode but unavailable for offline bundle; does not eliminate need for self-hosted storage |
| | | | | | Local filesystem | No API for access control, no versioning, no lifecycle management, no encryption at rest |
| 17 | S3 client **(S)** | boto3 | >=1.35 | Universal S3 client. Works with MinIO, AWS S3, Hetzner Object Storage, and any S3-compatible store. No vendor lock-in. | minio-py | Ties code to MinIO specifically; boto3 is more portable |
| 18 | Task queue **(S)** | Celery | >=5.6 | Battle-tested task queue with task chains, retries, and dead-letter queues. Floor raised from >=5.4 to >=5.6 for memory leak fixes and Python 3.13 support (current release: 5.6.2). Handles the core requirement of async document processing with retry. | Temporal | Higher operational complexity (requires its own PostgreSQL and Elasticsearch); steep learning curve. Migrate to Temporal when pipeline complexity demands durable workflows |
| | | | | | Airflow | Designed for scheduled batch DAGs, not event-driven document processing; scheduler model adds latency |
| | | | | | Dramatiq | Smaller ecosystem; fewer monitoring tools and deployment guides |
| 19 | Queue broker **(S)** | Redis | >=8.0 (server) | Celery broker, caching layer, and rate limiting store. Floor raised from >=7.4 to >=8.0 per verified releases (Redis 8.4 is GA). Single service handles three concerns, reducing operational surface. | RabbitMQ | Additional operational component; Redis already needed for caching and rate limiting |
| 20 | Secrets management **(S)** | SOPS + age | SOPS >=3.9, age >=1.2 | Encrypted secrets in version control using age encryption. Per-tenant secrets files encrypted with tenant-specific age keys. Simpler operational model than Vault for <20 tenants. Migrate to HashiCorp Vault when dynamic secret rotation is required or tenant count exceeds 20. | HashiCorp Vault | Higher operational complexity (requires its own backend storage); warranted only when dynamic rotation needed or >20 tenants |
| | | | | | AWS / GCP KMS | Violates data sovereignty principle; breaks offline mode entirely |
| | | | | | Environment variables alone | No encryption at rest, no rotation, no access audit; inadequate for per-tenant credentials |
| 21 | Reverse proxy / API gateway **(S)** | Traefik | v3 | Lightweight reverse proxy with automatic TLS termination, routing, and rate limiting. Docker-native with label-based configuration. Suitable for self-hosted Hetzner environments. | Caddy | Viable alternative but Traefik has stronger Docker integration and more mature load-balancing features |
| | | | | | Kong | Too heavy for this use case; designed for API management at hyperscaler scale |
| | | | | | AWS API Gateway | Not self-hosted; violates sovereignty |
| 22 | Structured logging **(S)** | structlog | >=25.1 | Produces JSON-formatted logs that are machine-parseable. Bound context (tenant_id, job_id, document_id) propagates through the call stack without manual threading. Floor raised from >=24.4 to >=25.1 per verified releases (current: 25.5.0). | stdlib logging | No structured output; no bound context propagation; requires manual formatting |
| 23 | Metrics collection **(S)** | Prometheus | >=3.5 | Pull-based metrics collection, standard for containerized workloads. Prometheus 3.x is the current major release line. Floor raised from >=2.54 to >=3.5 (LTS release: 3.5.1). | Datadog | SaaS monitoring violates data sovereignty |
| | | | | | New Relic | SaaS monitoring violates data sovereignty |
| | | | | | InfluxDB | Less ecosystem integration with Grafana and container orchestration |
| 24 | Dashboards **(S)** | Grafana | >=11 (OSS edition) | Pairs with Prometheus for metrics visualization and Loki for log exploration. Single pane of glass for pipeline health per tenant. | Kibana | Tied to Elasticsearch; ELK stack is too resource-heavy for per-tenant VMs |
| 25 | Log aggregation **(S)** | Loki | >=3.2 | Lightweight log aggregation designed to work with Grafana. Does not require Elasticsearch. Accepts structured JSON logs from structlog via Promtail. | Elasticsearch (ELK) | Too resource-heavy (2GB+ heap minimum) for per-tenant VMs on Hetzner |
| 26 | HTTP client **(S)** | httpx | >=0.27 | Async HTTP client for OpenRouter API calls and Hetzner Cloud API calls. Drop-in replacement for requests with native async support. | requests | No async support; blocks the event loop in FastAPI handlers |
| | | | | | aiohttp | httpx has a cleaner API and better type annotations |
| 27 | Retry logic **(S)** | tenacity | >=9.0 | Configurable retry with exponential backoff for transient failures (OpenRouter rate limits, Hetzner API timeouts, network blips). Decorator-based API integrates cleanly with async functions. | Custom retry loops | Error-prone; tenacity handles edge cases (jitter, max delay, retry conditions) correctly |
| 28 | JWT handling **(S)** | python-jose[cryptography] | >=3.3 | JWT token creation and validation for tenant authentication at the intake gateway and serving layer. The `[cryptography]` extra uses the cryptography library backend for JOSE operations. | PyJWT | Acceptable alternative; python-jose provides a more complete JOSE implementation including JWE if needed |
| 29 | File upload handling **(S)** | python-multipart | >=0.0.9 | Required by FastAPI for file upload parsing in the intake gateway. Handles multipart/form-data requests. | Manual parsing | Unnecessary complexity; python-multipart is the FastAPI standard |
| 30 | MIME detection **(S)** | python-magic | >=0.4.27 | Content-based MIME type detection using libmagic. Used in the intake gateway to enforce the file-type allowlist. Detects actual file type regardless of extension, preventing extension spoofing. | mimetypes (stdlib) | Extension-based only; does not detect actual file content type; trivially spoofable |
| 31 | Encryption **(S)** | cryptography | >=43 | Per-tenant document-at-rest encryption using Fernet or AES-GCM. Industry-standard Python cryptography library maintained by the Python Cryptographic Authority. | PyCryptodome | Less actively maintained; cryptography library has stronger community backing and better API design |
| 32 | Malware scanning **(S)** | ClamAV | >=1.4 (clamd sidecar container) | Intake gateway malware scanning for uploaded documents. Runs as a sidecar container with clamd socket communication. Works offline with bundled signature database (main.cvd, daily.cvd, bytecode.cvd). | Commercial AV | Licensing complexity; breaks offline mode; ClamAV is sufficient for document-format malware |
| 33 | Hetzner SDK **(S)** | hcloud | >=2.10 | Python SDK for Hetzner Cloud API. Used by the control plane provisioning orchestrator for per-tenant server, network, firewall, and volume creation. Floor raised from >=2.2 to >=2.10 per verified releases (current: 2.16.0). | Raw HTTP API calls | Unnecessary complexity; SDK handles auth, pagination, and error handling |
| 34 | Container runtime **(S)** | Docker | >=27 | Standard container runtime. All services are containerized for both online and offline deployment modes. | Podman | Smaller ecosystem; Docker is the industry standard and required for Docker Compose compatibility |
| 35 | Prometheus instrumentation **(S)** | prometheus-fastapi-instrumentator | >=7.0 | Automatic HTTP metrics instrumentation for FastAPI. Exposes request duration, count, and size metrics to Prometheus without manual instrumentation code. | Manual Prometheus client | Unnecessary boilerplate; the instrumentator handles standard HTTP metrics automatically |

### 1.3 Resolved Open Questions

The following open questions from Phase 1 research (01-RESEARCH.md) are resolved with final decisions:

#### 1. MinIO Maintenance Mode

**Decision: Continue with MinIO (Option A -- pragmatic).**

MinIO community edition entered maintenance mode in December 2025. No new features, PRs, or enhancements will be accepted. Security fixes are evaluated case-by-case. The web management console was already removed from the community edition in February 2025.

**Rationale:** The S3 API implementation in MinIO is stable and feature-complete for this use case (bucket CRUD, object CRUD, server-side encryption, versioning, lifecycle policies). The codebase is mature with years of production use. For a planning pack that must be executable now, MinIO is the lowest-risk choice. All application code uses boto3 with S3-compatible endpoints, making any future migration a configuration change with zero code modifications.

**Migration target:** Garage (Rust, Apache 2.0, v2.0) is documented as the migration target if MinIO is abandoned entirely. Garage provides an S3-compatible API and is actively developed. Migration would involve: (1) deploying Garage alongside MinIO, (2) syncing bucket contents via `mc mirror` or `aws s3 sync`, (3) updating endpoint configuration, (4) decommissioning MinIO. No application code changes required.

#### 2. Embedding Dimension Alignment

**Decision: Both modes locked to 768 dimensions.**

- **Online mode:** OpenRouter `text-embedding-3-small` with `dimensions=768` parameter. OpenAI's text-embedding-3-small supports dimension reduction via the API, producing a 768-dimensional vector from its native 1536-dimensional space.
- **Offline mode:** Nomic embed-text v1.5 at native 768 dimensions. No dimension reduction needed; 768d is the model's native output.

**Rationale:** Locking both modes to 768d enables cross-mode vector compatibility. Vectors created in online mode can be queried in offline mode and vice versa (with the caveat documented in Section 4 that semantic similarity may differ slightly between models). This eliminates the dimension mismatch pitfall (PITFALLS.md Mod1) by construction.

**Dimension assertion:** The embedding service must assert that every vector has exactly 768 dimensions before writing to Qdrant. Vectors with unexpected dimensions must be rejected with an error, never silently stored.

#### 3. Nomic v1.5 vs v2 for Offline Mode

**Decision: Lock to Nomic embed-text v1.5.**

Nomic embed-text v2 (MoE architecture, 475M parameters) offers improved multilingual support and retrieval quality. However, local inference via Ollama is announced as "coming soon" with no confirmed release date. The planning pack must be executable with confirmed, production-ready tooling.

**Rationale:** v1.5 is confirmed working for local inference via GPT4All on both CPU and GPU. GGUF quantized versions are available for resource-constrained environments (~275MB for Q8_0 GGUF vs ~550MB for full weights). v1.5 produces 768d vectors natively, aligning with the online mode configuration.

**Future upgrade path:** When Nomic v2 local inference is confirmed and tested, upgrade by: (1) deploying v2 model alongside v1.5, (2) re-embedding tenant documents with v2 into a shadow collection, (3) validating retrieval quality, (4) swapping the active collection. Full re-indexing is required because v1.5 and v2 produce semantically different vectors despite the same dimensionality.

#### 4. Qdrant: Collection-Per-Tenant vs Tiered Multitenancy

**Decision: Collection-per-tenant.**

Qdrant 1.16 (released November 2025) introduces tiered multitenancy with shared fallback shards for small tenants and dedicated shards for large tenants via "promotion." This is an optimization for platforms with many small tenants sharing infrastructure.

**Rationale:** Frostbyte's isolation-by-construction principle requires that no tenant's data shares physical storage with another tenant's data, even with payload-based filtering. Shared shards in tiered multitenancy rely on correct filter application at every query -- a single missing filter clause leaks cross-tenant data. Collection-per-tenant provides structural isolation: each tenant's vectors exist in a separate collection with separate API key scoping. There is no query path that could accidentally return another tenant's vectors.

**Trade-off acknowledged:** Collection-per-tenant incurs higher resource overhead (each collection has its own HNSW index, WAL, and memory allocation). This is acceptable for the target scale of 5-50 tenants. If tenant count grows beyond 50 with many small tenants, tiered multitenancy with a "shared infrastructure" tier (for non-regulated tenants only) is a documented future optimization.

---

## Section 2: Online Mode Dependency Manifest (TECH-02)

This section provides a complete dependency specification for the online (cloud-hosted, internet-connected) deployment mode. An engineer can use this section alone to set up the full development and production environment.

### 2.1 Python Packages

Organized by layer in pyproject.toml format. All version floors match Section 1 decisions.

```toml
[project]
name = "frostbyte-etl"
requires-python = ">=3.12"

[project.dependencies]
# API layer
fastapi = ">=0.115"
uvicorn = {version = ">=0.30", extras = ["standard"]}
pydantic = ">=2.10"
pydantic-settings = ">=2.5"
python-multipart = ">=0.0.9"
python-jose = {version = ">=3.3", extras = ["cryptography"]}
httpx = ">=0.27"

# Database layer
sqlalchemy = {version = ">=2.0.46", extras = ["asyncio"]}
asyncpg = ">=0.29"
alembic = ">=1.13"

# Task queue layer
celery = {version = ">=5.6", extras = ["redis"]}
redis = ">=5.2"

# Storage layer
boto3 = ">=1.35"
qdrant-client = ">=1.13"

# Parsing layer (client-specified)
docling = ">=2.70"
unstructured = {version = ">=0.16", extras = ["all-docs"]}

# Security layer
cryptography = ">=43"
python-magic = ">=0.4.27"

# Observability layer
structlog = ">=25.1"
prometheus-fastapi-instrumentator = ">=7.0"

# Resilience layer
tenacity = ">=9.0"

# Infrastructure layer
hcloud = ">=2.10"
```

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "ruff>=0.7",
    "mypy>=1.12",
    "pre-commit>=3.8",
]
```

**Notes:**
- The `redis` Python package (>=5.2) is the client library. Redis server version (>=8.0) is specified in the Docker images section below.
- The `sqlalchemy[asyncio]` extra installs the greenlet dependency required for async session support. This is mandatory since SQLAlchemy 2.0.46+ no longer auto-installs it.
- The `unstructured[all-docs]` extra installs parsers for all supported document formats (PDF, DOCX, XLSX, PPTX, HTML, TXT, images).

### 2.2 Docker Images

Organized by service. For production offline bundles, pin by digest (`@sha256:...`). For the planning pack, version tags are sufficient and more readable.

| Service | Image | Version Tag | Purpose |
|---------|-------|-------------|---------|
| PostgreSQL | `postgres` | `16-alpine` | Relational DB for governance metadata, lineage, audit, job state |
| Redis | `redis` | `8-alpine` | Celery broker, caching, rate limiting |
| Qdrant | `qdrant/qdrant` | `v1.13.0` | Vector store with per-tenant collections |
| MinIO | `minio/minio` | `latest` | S3-compatible object storage (per-tenant buckets) |
| ClamAV | `clamav/clamav` | `1.4` | Malware scanning sidecar for intake gateway |
| Traefik | `traefik` | `v3` | Reverse proxy, TLS termination, API gateway |
| Prometheus | `prom/prometheus` | `v3.5.1` | Metrics collection (LTS release) |
| Grafana | `grafana/grafana` | `11-oss` | Dashboards and alerting |
| Loki | `grafana/loki` | `3.2` | Log aggregation |
| Promtail | `grafana/promtail` | `3.2` | Log shipping agent (containers to Loki) |

### 2.3 ML Models (Online Mode)

| Model | Provider | Access Method | Dimensions | Configuration | Use Case |
|-------|----------|---------------|------------|---------------|----------|
| text-embedding-3-small | OpenRouter (OpenAI) | HTTP API (`/api/v1/embeddings`) | 768 (configured via `dimensions` parameter) | `model: "openai/text-embedding-3-small"`, `dimensions: 768` | Document chunk embedding for RAG retrieval |

**Note:** The model's native output is 1536 dimensions. The `dimensions=768` parameter instructs the API to return a 768-dimensional vector, matching the offline mode Nomic embed-text v1.5 output. This parameter is supported by OpenAI's text-embedding-3 model family.

---

## Section 3: Offline Mode Dependency Manifest (TECH-03)

The offline manifest is a **strict superset** of the online manifest (Section 2). Every package, image, and model from Section 2 is included. This section documents the additional dependencies required for air-gapped operation.

### 3.1 Python Packages

All Python packages from Section 2.1 are included in the offline bundle. No additional Python packages are required for offline mode -- the same application code runs in both modes, with configuration determining whether to call OpenRouter (online) or the local Nomic model (offline) for embeddings.

### 3.2 Docker Images

All Docker images from Section 2.2 are included in the offline bundle, saved as `.tar` files via `docker save`. The following images are additional offline-only services:

| Service | Image | Version Tag | Purpose | Approximate Compressed Size |
|---------|-------|-------------|---------|----------------------------|
| **All images from Section 2.2** | | | | |
| PostgreSQL | `postgres` | `16-alpine` | Same as online | ~90 MB |
| Redis | `redis` | `8-alpine` | Same as online | ~40 MB |
| Qdrant | `qdrant/qdrant` | `v1.13.0` | Same as online | ~120 MB |
| MinIO | `minio/minio` | `latest` | Same as online | ~150 MB |
| ClamAV | `clamav/clamav` | `1.4` | Same as online (bundled signatures) | ~300 MB |
| Traefik | `traefik` | `v3` | Not required for offline single-host | ~100 MB |
| Prometheus | `prom/prometheus` | `v3.5.1` | Optional for offline | ~100 MB |
| Grafana | `grafana/grafana` | `11-oss` | Optional for offline | ~150 MB |
| Loki | `grafana/loki` | `3.2` | Not included in offline mode | N/A |
| Promtail | `grafana/promtail` | `3.2` | Not included in offline mode | N/A |
| **Offline-only images** | | | | |
| Nomic embed-text | Custom (GPT4All-based) | v1.5 | Local embedding inference | ~500 MB |
| Application (API) | `frostbyte/api` | v1.0 | FastAPI application server | ~250 MB |
| Application (Worker) | `frostbyte/worker` | v1.0 | Celery worker for document processing | ~250 MB |

### 3.3 Local ML Model Weights

These model weights must be bundled in the offline archive. They are not downloaded at runtime.

| Model | Source | Version | Native Dimensions | File Format | Approximate Size | Checksum Requirement |
|-------|--------|---------|-------------------|-------------|------------------|---------------------|
| Nomic embed-text v1.5 | Hugging Face: `nomic-ai/nomic-embed-text-v1.5` | v1.5 | 768 | GGUF (quantized Q8_0) for resource-constrained environments; full weights for maximum quality | ~275 MB (Q8_0 GGUF) / ~550 MB (full weights) | SHA-256 hash verified at bundle build time; hash recorded in `MANIFEST.json` |
| PII / NER model | spaCy `en_core_web_lg` or Presidio analyzer | Latest at bundle build time | N/A (NLP, not embedding) | spaCy model package (`.tar.gz`) | ~750 MB | SHA-256 hash verified at bundle build time; hash recorded in `MANIFEST.json` |

**Offline embedding routing:** The application configuration for offline mode points the embedding service to the local Nomic container instead of OpenRouter. The same embedding interface is used; only the endpoint URL changes. No code branching is required.

### 3.4 ClamAV Signature Database

ClamAV requires a signature database to detect malware. In offline mode, signatures are bundled and cannot be updated over the network.

| Component | Source | Update Mechanism | Approximate Size |
|-----------|--------|------------------|------------------|
| `main.cvd` | `clamav.net/downloads` | Shipped in bundle; updated via signed tarball on sneakernet | ~160 MB |
| `daily.cvd` | `clamav.net/downloads` | Shipped in bundle; updated via signed tarball on sneakernet | ~120 MB |
| `bytecode.cvd` | `clamav.net/downloads` | Shipped in bundle; updated via signed tarball on sneakernet | ~1 MB |

**Security trade-off:** Offline ClamAV signatures freeze at bundle build time. New malware signatures released after the bundle is built will not be detected until the next bundle update is delivered via sneakernet. This trade-off is inherent to air-gapped operation and is documented for operator awareness.

**Update procedure:** When a new signature database is available, Frostbyte packages the updated `.cvd` files into a signed tarball. The operator verifies the signature, extracts the files to the ClamAV data volume, and restarts the ClamAV container. No full bundle rebuild is required for signature-only updates.

### 3.5 Total Bundle Size Estimate

| Category | Components | Estimated Size |
|----------|-----------|---------------|
| Docker images (compressed tarballs) | PostgreSQL, Redis, Qdrant, MinIO, ClamAV, Prometheus, Grafana, Nomic, API, Worker | ~2.0 GB |
| ML model weights | Nomic embed-text v1.5 (full) + PII/NER model | ~1.3 GB |
| ClamAV signatures | main.cvd + daily.cvd + bytecode.cvd | ~280 MB |
| Application code + configuration | docker-compose.yml, .env, policy rules, allowlists | ~10 MB |
| Scripts + documentation | install.sh, verify.sh, export.sh, MANIFEST.json | ~5 MB |
| **Estimated total (compressed)** | | **~3.6 GB** |
| **Estimated total (with safety margin)** | Including future growth, additional models, and overhead | **~5-7 GB** |

**Note:** The safety margin accounts for: (1) Docker image layer overlap reducing compression efficiency, (2) future model additions, (3) sample data for smoke tests, (4) documentation bundled with the archive. Plan for 8 GB of transfer media (USB drive or secure file transfer) to accommodate the bundle plus verification artifacts.

### 3.6 Offline-Specific Configuration

| Concern | Offline Configuration | Rationale |
|---------|----------------------|-----------|
| Embedding routing | Nomic embed-text v1.5 container (local, no outbound network calls) | Air-gapped operation; no access to OpenRouter |
| Audit stream | Local append-only PostgreSQL table (single tenant) | No central audit plane to aggregate to; all audit data stays local |
| Docker network | `internal: true` on all service networks | Structural guarantee of no outbound connectivity, regardless of host firewall configuration |
| Monitoring | Prometheus + Grafana optional (included but not required for operation) | Operators may not have monitoring expertise; pipeline functions without it |
| Log aggregation | Docker log driver only (`docker compose logs`) | Loki not included in offline mode; operational logs accessible via Docker commands |
| Tenant configuration | Static `docker-compose.yml` with single tenant | No Hetzner Cloud API access; exactly one tenant per offline deployment |
| Secrets | SOPS + age (pre-decrypted at bundle build time) or static `.env` file | No dynamic secret rotation in air-gapped environments |

---

## Section 4: Cross-Mode Compatibility Matrix

This section documents every component with its online and offline versions and whether data can be transferred between modes.

### 4.1 Component Compatibility Table

| Component | Online Mode | Offline Mode | Data Transferable? | Notes |
|-----------|-------------|--------------|-------------------|-------|
| API framework | FastAPI (same codebase) | FastAPI (same codebase) | N/A | Identical application code; mode determined by configuration |
| Relational DB | PostgreSQL 16 (per-tenant instance) | PostgreSQL 16 (single container) | Yes (`pg_dump` / `pg_restore`) | Schema identical across modes; tenant_id column present in both |
| Vector store | Qdrant (per-tenant collection) | Qdrant (single collection) | Yes (snapshot export/import) | Both use 768d vectors; collection structure identical |
| Object storage | MinIO (per-tenant bucket) | MinIO (single bucket) | Yes (`mc mirror` or `aws s3 sync`) | S3 API identical; bucket structure and object keys match |
| Embeddings | OpenRouter text-embedding-3-small (768d) | Nomic embed-text v1.5 (768d) | Yes (same dimension) | Vectors are cross-compatible in dimension; see Explicit Divergences below |
| Task queue | Celery + Redis | Celery + Redis | N/A | Identical configuration; same task definitions |
| Malware scanning | ClamAV (live signature updates) | ClamAV (bundled signatures) | N/A | Scan results comparable; offline signatures may lag |
| Audit stream | PostgreSQL (append-only, central audit plane) | PostgreSQL (append-only, local) | Yes (JSON Lines export) | Export format identical; offline audit can be imported into online audit plane |
| Monitoring | Prometheus + Grafana + Loki | Prometheus + Grafana (optional) | N/A | No Loki in offline mode; Prometheus metrics format identical |
| Secrets | SOPS + age (per-tenant age keys) | SOPS + age (or static `.env`) | N/A | Same encryption mechanism; offline may use pre-decrypted static config |
| API gateway | Traefik (TLS, routing, rate limiting) | Not required (single-host, no TLS needed) | N/A | Offline bundle is accessed via localhost only |
| Tenant provisioning | Hetzner Cloud API (dynamic) | Static `docker-compose.yml` | N/A | Offline has exactly one tenant; no dynamic provisioning |
| Networking | Per-tenant Hetzner firewall rules | Docker `internal: true` network | N/A | Both achieve zero cross-tenant traffic by construction |
| Document parsing | Docling + Unstructured (same code) | Docling + Unstructured (same code) | N/A | Identical parsing pipeline; same canonical JSON output |
| PII detection | Policy engine (same rules) | Policy engine (same rules) | N/A | Same detection patterns and thresholds |
| Injection defense | Policy engine (same rules) | Policy engine (same rules) | N/A | Same scoring heuristics and quarantine thresholds |

### 4.2 Explicit Divergences

The following are documented differences between online and offline modes that operators and engineers must be aware of:

**Divergence 1: Embedding Model Differences**

Online mode uses OpenRouter's `text-embedding-3-small` (an OpenAI model). Offline mode uses Nomic embed-text v1.5. Both produce 768-dimensional vectors, enabling storage and retrieval compatibility. However, the two models produce **semantically similar but not identical** vector representations. A query vector generated by one model will return reasonable but potentially different ranking results when searched against vectors generated by the other model.

**Impact:** If data migrates from offline to online (or vice versa), full re-indexing with the target mode's embedding model is recommended for optimal retrieval quality. Cross-mode search will function but may produce suboptimal ranking.

**Divergence 2: Audit Stream Aggregation**

Online mode aggregates audit events from all tenant data planes into a central audit plane (shared, append-only PostgreSQL). Offline mode keeps audit events local to the single-tenant deployment in a local PostgreSQL table.

**Impact:** When an offline deployment later connects to the online infrastructure (e.g., the customer brings the offline environment online), the local audit log can be exported as JSON Lines and imported into the central audit plane. The export format is identical, enabling seamless migration. During offline operation, there is no central audit visibility.

**Divergence 3: ClamAV Signature Currency**

Online mode can update ClamAV signatures via the internet (`freshclam` daemon). Offline mode's signatures freeze at bundle build time.

**Impact:** Offline deployments may not detect malware that uses signatures released after the bundle was built. This is a documented security trade-off inherent to air-gapped operation. Mitigation: signature-only update tarballs can be delivered via sneakernet without rebuilding the full bundle.

**Divergence 4: Log Aggregation**

Online mode uses Loki for centralized, searchable log aggregation with Grafana exploration. Offline mode uses Docker's built-in log driver, accessible via `docker compose logs`.

**Impact:** Operational log search in offline mode is limited to Docker CLI commands. There is no full-text log search or log correlation across services. This is acceptable because: (1) audit logs (the compliance-critical data) are always stored in PostgreSQL, not in operational logs, and (2) offline deployments have a single tenant with a simpler operational surface.

---

## Section 5: Version Pin Update Procedure

This section describes how to update the version pins in this document as dependencies release new versions.

### 5.1 Update Cadence

Perform a version audit **quarterly** (or when a security advisory is published for any dependency). The audit covers:

1. **Python packages:** Check PyPI for each package listed in Section 2.1.
2. **Docker images:** Check Docker Hub and upstream release pages for each image in Section 2.2.
3. **ML models:** Check Hugging Face and model provider release notes for each model in Sections 2.3 and 3.3.
4. **ClamAV signatures:** Updated independently via the signature update procedure (Section 3.4).

### 5.2 Update Steps

1. **Run a version audit script.** For each dependency, query the package registry (PyPI, Docker Hub, GitHub Releases) and compare the current latest version against the floor specified in this document.

2. **Evaluate breaking changes.** For each dependency with a new major or minor version, read the changelog and identify breaking changes that affect this project.

3. **Update the version floors in this document.** Raise version floors only when the new version provides a required fix (security, compatibility) or when the old floor is no longer available.

4. **Update the offline bundle.** Rebuild all Docker images with the new dependencies. Re-download model weights if updated. Regenerate SHA-256 hashes for all bundle components.

5. **Run the full test suite.** Execute unit tests, integration tests, and end-to-end tests against the updated dependencies. All tests must pass before the version floor is officially raised.

6. **Verify hash integrity.** For the offline bundle, verify that all SHA-256 hashes in `MANIFEST.json` match the rebuilt components.

7. **Document the change.** Record the version update in the project CHANGELOG with: the dependency name, old version floor, new version floor, reason for the update, and the date.

### 5.3 Emergency Security Updates

When a security advisory (CVE) is published for a dependency:

1. **Assess impact.** Determine whether the vulnerability affects this project's usage of the dependency.
2. **If affected:** Update the version floor immediately, rebuild the offline bundle, and release a patch.
3. **If not affected:** Document the CVE and the reason it does not apply. Update the version floor at the next scheduled audit if a fixed version is available.
4. **Notify operators.** For offline deployments, deliver the updated bundle or component tarball via sneakernet with the CVE advisory included.
