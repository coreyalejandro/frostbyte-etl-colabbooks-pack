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
