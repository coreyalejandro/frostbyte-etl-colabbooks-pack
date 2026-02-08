# Technology Stack

**Project:** Frostbyte Multi-Tenant Document ETL Pipeline
**Researched:** 2026-02-08
**Overall confidence:** MEDIUM (versions need PyPI/release verification; architectural choices are HIGH confidence)

> **Research note:** Context7, WebSearch, and WebFetch were unavailable during this research session. All version numbers are based on training data (cutoff May 2025) and MUST be verified against PyPI / official releases before implementation. Architectural recommendations are based on well-established patterns and carry HIGH confidence regardless.

---

## Locked-In Decisions (DECIDED -- Not Recommendations)

These were specified by the client (Frode / Frostbyte) and are non-negotiable. They are documented here for completeness and to show how the recommended stack complements them.

| Technology | Role | Status | Source |
|---|---|---|---|
| **Python** | Primary language (ETL + API + tooling) | DECIDED | Client requirement |
| **Hetzner Cloud** | Per-tenant infrastructure provisioning | DECIDED | Client requirement |
| **Docling** | Document conversion + layout-aware structuring | DECIDED | Client requirement |
| **Unstructured (OSS)** | Partitioning/chunking primitives + metadata enrichment | DECIDED | Client requirement |
| **OpenRouter** | Online embeddings endpoint (OpenAI / Qwen / Kimi models) | DECIDED | Client requirement |
| **Nomic embed-text** | Offline / air-gapped embeddings (local inference) | DECIDED | Client requirement |
| **Docker Compose** | Offline bundle orchestration (air-gapped mode) | DECIDED | Implied by offline requirement |

---

## Recommended Stack

### API Framework

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **FastAPI** | >=0.115 | HTTP API framework for intake gateway, serving layer, and control plane | HIGH | De facto standard for Python async APIs. Native OpenAPI spec generation means the serving layer and intake gateway get automatic documentation. Pydantic v2 integration provides input validation (critical for untrusted document metadata). Async-first design aligns with I/O-heavy ETL workloads (file uploads, DB writes, embedding API calls). Starlette foundation provides middleware hooks for tenant auth, rate limiting, and audit logging. |
| **Uvicorn** | >=0.30 | ASGI server | HIGH | Standard production server for FastAPI. Pairs with Gunicorn for multi-worker process management. |
| **Pydantic** | >=2.9 | Data validation + serialization | HIGH | Already a FastAPI dependency. Use for all internal schemas: structured document JSON, intake receipts, audit events, API request/response models. Pydantic v2's Rust-backed core gives 5-50x validation speedup over v1. |

**Why not Litestar:** Litestar is technically excellent and arguably more opinionated (which this project would benefit from), but FastAPI's ecosystem is 10x larger. When hiring engineers or onboarding AI agents, FastAPI knowledge is nearly universal. For an audition deliverable where implementation will be handed off, minimize onboarding friction.

**Why not Django REST Framework:** Django's ORM and sync-first model add overhead for an ETL pipeline that is fundamentally async I/O. Django's batteries (admin, auth, sessions) are irrelevant here -- tenant auth is custom, there is no user-facing admin panel.

**Why not Flask:** No async support without extensions, no built-in validation, no OpenAPI generation. Flask requires assembling what FastAPI provides out of the box.

### Relational Database

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **PostgreSQL** | >=16 | Governance metadata, lineage, job states, retention rules, tenant registry, audit log | HIGH | Only serious choice for regulated multi-tenant workloads. Row-level security (RLS) provides defense-in-depth for tenant isolation. JSONB columns handle semi-structured metadata (parse results, enrichment outputs) without requiring a separate document store. Mature ecosystem for backups, replication, and point-in-time recovery -- all required for audit compliance. |
| **SQLAlchemy** | >=2.0 | Python ORM + connection management | HIGH | SQLAlchemy 2.0's new-style query API is cleaner and fully typed. Async support via `asyncpg` driver. Alembic (same project) handles schema migrations. |
| **Alembic** | >=1.13 | Database migrations | HIGH | Standard migration tool for SQLAlchemy. Deterministic, version-controlled schema changes are required for audit compliance. |
| **asyncpg** | >=0.29 | Async PostgreSQL driver | HIGH | Fastest Python PostgreSQL driver. Native async, no wrapper overhead. Required for FastAPI's async request handlers to avoid blocking the event loop on DB queries. |

**Why not MySQL/MariaDB:** No row-level security. Weaker JSONB support. Fewer extensions relevant to this workload (pgvector, pg_cron). PostgreSQL is the standard for regulated data workloads.

**Why not CockroachDB:** Over-engineered for this use case. Frostbyte provisions per-tenant PostgreSQL instances on Hetzner, so distributed SQL across tenants is not needed. CockroachDB adds operational complexity with no benefit when each tenant has its own isolated DB.

**Why not SQLite:** Not suitable for concurrent multi-process access in the online API mode. Could be used inside the offline Docker bundle for the relational store, but PostgreSQL in a container is equally lightweight and keeps the schema identical across modes.

### Tenant Isolation Strategy for PostgreSQL

**Online mode:** Each tenant gets a dedicated PostgreSQL instance (or a dedicated database within a shared cluster with RLS). The control plane's tenant registry maps `tenant_id` to connection strings. Application code NEVER constructs cross-tenant queries.

**Offline mode:** Single PostgreSQL container in Docker Compose. Only one tenant exists in the bundle by definition.

### Vector Store

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **Qdrant** | >=1.12 (server), >=1.12 (Python client) | Per-tenant vector storage for embeddings | HIGH | Purpose-built vector DB with native multi-tenancy support via collections (one collection per tenant) or payload-based filtering with tenant_id. Supports both gRPC and REST APIs. Built-in snapshot/backup for compliance. Runs as a single binary or Docker container -- critical for the offline bundle. Handles both dense and sparse vectors if hybrid search is needed later. |

**Why not pgvector:** pgvector is acceptable for moderate scale (<1M vectors per tenant) and reduces operational surface by keeping vectors in PostgreSQL. However, for a pipeline that will ingest thousands of documents with thousands of chunks each, Qdrant provides: (1) purpose-built HNSW indexing with better recall/latency at scale, (2) native collection-level isolation (cleaner than schema-per-tenant in Postgres), (3) built-in snapshot export for the offline bundle. **Fallback:** If operational simplicity is prioritized over retrieval performance, pgvector >=0.7 with HNSW index support is a viable alternative. Document this as a per-tenant decision.

**Why not Weaviate:** Weaviate is heavier operationally (requires more memory, more complex configuration). Its module system adds unnecessary abstraction when embeddings are already handled externally (OpenRouter / Nomic). Qdrant is leaner for "bring your own vectors" workflows.

**Why not ChromaDB:** ChromaDB is designed for prototyping and single-user workloads. No production multi-tenancy, limited backup/restore, not suitable for regulated environments.

**Why not Milvus:** Over-engineered for per-tenant isolated deployments. Milvus shines at massive scale (billions of vectors in a shared cluster), which is the opposite of Frostbyte's model.

### Object Storage

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **MinIO** | latest (self-hosted) | S3-compatible object storage for raw documents, normalized artifacts, export bundles | HIGH | S3-compatible API means all code uses `boto3` / `s3fs`, making it portable if a tenant later moves to AWS S3 or Hetzner Object Storage. Runs as a single binary or Docker container (offline bundle compatible). Built-in bucket policies provide tenant isolation (one bucket per tenant). Supports server-side encryption, versioning, and lifecycle policies -- all required for document retention compliance. |
| **boto3** | >=1.35 | Python S3 client | HIGH | Universal S3 client. Works with MinIO, AWS S3, and any S3-compatible store. No vendor lock-in. |

**Why not Hetzner Object Storage directly:** Hetzner Object Storage is S3-compatible and viable for online mode. However, MinIO provides the same API locally for the offline bundle. Using MinIO consistently across both modes eliminates mode-specific code paths. For online mode, a per-tenant MinIO instance on Hetzner is recommended; migrating to Hetzner Object Storage is a future optimization that requires zero code changes.

**Why not local filesystem:** No API for access control, no versioning, no lifecycle management, no encryption at rest. Documents are untrusted inputs requiring governed storage.

### Task Orchestration

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **Temporal** | Server >=1.24, Python SDK (temporalio) >=1.7 | Workflow orchestration for ETL pipeline phases | MEDIUM | Temporal provides durable, retryable workflows with built-in visibility into pipeline state. Each ETL pipeline run (intake -> parse -> enrich -> store -> index) maps naturally to a Temporal workflow with activities for each phase. Key advantages for this use case: (1) automatic retry with backoff for transient failures (OpenRouter API rate limits, Hetzner API timeouts), (2) workflow history provides an audit trail of every step, (3) child workflows enable per-document parallelism within a batch, (4) deterministic replay means failed pipelines resume from the exact failure point. |

**Why MEDIUM confidence:** Temporal adds significant operational complexity (requires its own PostgreSQL database, Elasticsearch/OpenSearch for visibility). For a team unfamiliar with Temporal, the learning curve is steep. The alternative below is lower-risk.

**Simpler alternative -- Celery + Redis:**

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **Celery** | >=5.4 | Task queue for async ETL jobs | HIGH (maturity) | Battle-tested, widely understood, smaller operational footprint. |
| **Redis** | >=7.4 | Celery broker + result backend | HIGH | Fast, lightweight, runs in Docker. Also useful for caching and rate limiting. |

**Recommendation:** Start with **Celery + Redis** for the initial implementation. Migrate to Temporal when pipeline complexity demands durable workflows (e.g., multi-stage approval gates, long-running enrichment jobs, cross-service orchestration). Celery handles the core requirement (async document processing with retry) without the operational overhead of Temporal.

**Why not Dramatiq:** Dramatiq is cleaner than Celery but has a much smaller ecosystem. Fewer monitoring tools, fewer deployment guides, fewer engineers with experience. For a regulated pipeline where observability matters, Celery's Flower dashboard and mature integrations win.

**Why not Airflow:** Airflow is designed for scheduled batch DAGs, not event-driven document processing. The ETL pipeline triggers on document upload (event-driven), not on a cron schedule. Airflow's scheduler model adds latency and complexity for this pattern.

**Why not Prefect / Dagster:** These are data pipeline orchestrators optimized for analytics/ML workflows with DAG visualization. They add abstraction over what is fundamentally a task queue problem. The pipeline's phases are linear per-document, not complex DAGs.

### Audit Logging

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **PostgreSQL (append-only audit table)** | (same instance) | Immutable audit stream for all pipeline events | HIGH | The simplest approach that meets the requirement. An append-only table with a trigger that prevents UPDATE/DELETE provides immutability. Schema: `(event_id UUID, tenant_id, event_type, entity_type, entity_id, payload JSONB, created_at TIMESTAMPTZ, actor)`. A PostgreSQL advisory lock or trigger-based constraint prevents mutation. |
| **structlog** | >=24.4 | Structured logging throughout the application | HIGH | Produces JSON-formatted logs that are machine-parseable. Bound context (tenant_id, job_id, document_id) propagates through the call stack without manual threading. Critical for correlating events across pipeline phases. |

**Why append-only PostgreSQL and not a dedicated event store (EventStoreDB, Kafka):** For the scale of this pipeline (tens of tenants, thousands of documents per batch), a dedicated event store is over-engineered. The audit stream is append-only reads + writes, not a streaming platform. PostgreSQL handles this with a trigger that raises an exception on UPDATE/DELETE. If scale demands it later, the audit table's schema maps cleanly to Kafka topics.

**Why not just application logs:** Application logs are operational (debugging, monitoring). Audit logs are compliance artifacts (who did what, when, to which document, with what result). They have different retention policies, access controls, and query patterns. Mixing them violates separation of concerns.

### Container Orchestration

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **Docker Compose** | >=2.29 | Offline bundle orchestration | DECIDED | Client requirement for air-gapped mode. |
| **Docker** | >=27 | Container runtime | HIGH | Standard container runtime. |
| **K3s** | >=1.31 | Lightweight Kubernetes for online per-tenant orchestration | MEDIUM | K3s is a CNCF-certified Kubernetes distribution that runs in <512MB RAM. For Hetzner's per-tenant provisioning model, K3s provides namespace isolation, network policies, resource quotas, and rolling deployments without the operational weight of full Kubernetes. Each Hetzner tenant environment runs a K3s single-node cluster (or joins a shared K3s cluster with namespace isolation). |

**Simpler alternative -- Docker Compose for online mode too:** If the team is not ready for Kubernetes, run online mode as Docker Compose on per-tenant Hetzner VMs. This is operationally simpler and matches the offline bundle's orchestration model exactly. Trade-off: no native rolling deploys, no health-check-based restart, manual scaling.

**Recommendation:** Start with **Docker Compose everywhere** (online and offline). Introduce K3s when tenant count exceeds what manual Docker Compose management can handle (roughly >10 tenants). The application code is container-based either way, so the migration is infrastructure-only.

**Why not full Kubernetes (k8s):** Operational overhead is unjustifiable for per-tenant single-node deployments on Hetzner. K3s gives 95% of the benefit at 10% of the operational cost.

**Why not Nomad:** HashiCorp's licensing changes (BSL) create uncertainty for regulated deployments. K3s is Apache 2.0 and CNCF-backed.

### Secrets Management

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **HashiCorp Vault (Community)** | >=1.17 | Per-tenant secrets management (API keys, DB credentials, encryption keys) | MEDIUM | Vault provides dynamic secrets (auto-rotating DB credentials), encryption-as-a-service (transit engine for document encryption at rest), and per-tenant secret namespaces. The transit engine can serve as a lightweight KMS for per-tenant encryption keys without requiring AWS KMS or GCP KMS. Community edition is BSL-licensed but the use case (internal infrastructure, not resale) falls within permitted use. |

**Simpler alternative -- SOPS + age:**

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **SOPS** | >=3.9 | Encrypted secrets in version control | HIGH | Mozilla SOPS encrypts secret files (YAML/JSON/ENV) with age or PGP keys. Secrets are committed encrypted, decrypted at deploy time. Simpler operational model than Vault for <20 tenants. |
| **age** | >=1.2 | Encryption backend for SOPS | HIGH | Modern, simple encryption. No GPG key management complexity. |

**Recommendation:** Start with **SOPS + age** for the initial implementation. Each tenant's secrets file is encrypted with a tenant-specific age key. Migrate to Vault when: (1) dynamic secret rotation is required by compliance, (2) tenant count exceeds what SOPS file management can handle, or (3) encryption-as-a-service (transit engine) is needed.

**Why not AWS KMS / GCP KMS:** Frostbyte runs on Hetzner, not hyperscalers. Introducing a dependency on AWS/GCP for key management violates the sovereignty principle and breaks the offline bundle.

**Why not environment variables alone:** Environment variables are acceptable for non-secret configuration but inadequate for per-tenant API keys, DB credentials, and encryption keys. No encryption at rest, no rotation, no access audit.

### Monitoring + Observability

| Technology | Version | Purpose | Confidence | Why |
|---|---|---|---|---|
| **Prometheus** | >=2.54 | Metrics collection | HIGH | Pull-based metrics collection is standard for containerized workloads. FastAPI + Starlette expose metrics via `prometheus-fastapi-instrumentator`. Celery metrics via `celery-exporter`. PostgreSQL metrics via `postgres_exporter`. |
| **Grafana** | >=11 | Dashboards + alerting | HIGH | Pairs with Prometheus for metrics visualization. Pairs with Loki for log exploration. Single pane of glass for pipeline health. |
| **Loki** | >=3.2 | Log aggregation | HIGH | Lightweight log aggregation designed to work with Grafana. Does not require Elasticsearch. Accepts structured JSON logs from structlog via Promtail or Docker log driver. Lower operational footprint than ELK stack. |
| **Promtail** | (matches Loki) | Log shipping agent | HIGH | Ships container logs to Loki. Lightweight, Docker-native. |

**Why not ELK (Elasticsearch + Logstash + Kibana):** ELK is powerful but operationally heavy. Elasticsearch alone requires significant memory (2GB+ heap). For per-tenant deployments on Hetzner VMs, the resource overhead is unjustifiable. Loki + Grafana provides 80% of the functionality at 20% of the resource cost.

**Why not Datadog / New Relic / commercial APM:** SaaS monitoring services send telemetry data to external providers. This violates Frostbyte's data sovereignty principle for regulated tenants. All monitoring must be self-hosted.

**Offline bundle monitoring:** The offline Docker bundle includes Prometheus + Grafana as optional containers. Metrics are local-only. No Loki in offline mode (logs stay in Docker's log driver, viewable via `docker compose logs`).

### Additional Supporting Libraries

| Library | Version | Purpose | Confidence | When to Use |
|---|---|---|---|---|
| **Pydantic Settings** | >=2.5 | Configuration management from env vars + files | HIGH | All service configuration. Type-safe, validates at startup. |
| **tenacity** | >=9.0 | Retry logic with configurable backoff | HIGH | OpenRouter API calls, Hetzner API calls, any transient failure. |
| **python-multipart** | >=0.0.9 | File upload handling in FastAPI | HIGH | Intake gateway file upload endpoint. |
| **python-jose** or **PyJWT** | >=3.3 / >=2.9 | JWT token handling for tenant auth | HIGH | Intake gateway + serving layer authentication. |
| **ClamAV** (via clamd) | >=1.4 | Malware scanning for uploaded documents | HIGH | Intake gateway. Documents are untrusted inputs. ClamAV runs as a sidecar container. |
| **python-magic** | >=0.4.27 | MIME type detection | HIGH | Intake gateway file-type allowlist enforcement. |
| **cryptography** | >=43 | Encryption primitives for document-at-rest encryption | HIGH | Per-tenant document encryption before storage in MinIO. |
| **httpx** | >=0.27 | Async HTTP client | HIGH | OpenRouter API calls, Hetzner Cloud API calls. Replaces `requests` for async codebases. |
| **hcloud** | >=2.2 | Hetzner Cloud Python SDK | MEDIUM | Control plane tenant provisioning. Version needs verification. |

---

## Alternatives Considered (Summary)

| Category | Recommended | Alternative | Why Not |
|---|---|---|---|
| API Framework | FastAPI | Litestar | Smaller ecosystem, higher onboarding friction |
| API Framework | FastAPI | Django REST | Sync-first, batteries irrelevant to ETL |
| Relational DB | PostgreSQL | MySQL | No RLS, weaker JSONB, fewer compliance extensions |
| Relational DB | PostgreSQL | CockroachDB | Over-engineered for per-tenant isolated instances |
| Vector Store | Qdrant | pgvector | Acceptable fallback; weaker at scale, less clean isolation |
| Vector Store | Qdrant | Weaviate | Heavier operationally, module system adds unnecessary abstraction |
| Vector Store | Qdrant | ChromaDB | Not production-ready for multi-tenant regulated workloads |
| Object Storage | MinIO | Hetzner Object Storage | MinIO runs offline; same API, portable |
| Object Storage | MinIO | Local filesystem | No access control, no versioning, no encryption |
| Task Queue | Celery + Redis | Temporal | Higher operational complexity; migrate when needed |
| Task Queue | Celery + Redis | Airflow | Designed for scheduled DAGs, not event-driven processing |
| Task Queue | Celery + Redis | Dramatiq | Smaller ecosystem, fewer monitoring tools |
| Secrets | SOPS + age | HashiCorp Vault | Vault when dynamic rotation or >20 tenants needed |
| Secrets | SOPS + age | AWS/GCP KMS | Violates sovereignty; breaks offline mode |
| Monitoring | Prometheus + Grafana + Loki | ELK Stack | Too resource-heavy for per-tenant VMs |
| Monitoring | Prometheus + Grafana + Loki | Datadog / New Relic | SaaS violates data sovereignty |
| Container Orch | Docker Compose (start) | K3s | K3s when >10 tenants; Docker Compose everywhere first |
| Container Orch | Docker Compose (start) | Full Kubernetes | Unjustifiable overhead for single-node per-tenant |
| Logging | structlog | stdlib logging | No structured output, no bound context propagation |

---

## Stack Complementarity Map

How each recommended component fits with the locked-in choices:

```
Locked-In                  Recommended                  How They Connect
---------                  -----------                  ----------------
Docling + Unstructured --> Celery workers              Parse jobs dispatched as async tasks
                       --> MinIO                       Raw docs read from, normalized docs written to
                       --> PostgreSQL                  Parse metadata + lineage recorded
                       --> structlog                   Per-document parse events logged

OpenRouter             --> httpx                       Async HTTP client for embedding API calls
                       --> tenacity                    Retry with backoff for rate limits
                       --> Celery                      Embedding jobs queued after parsing
                       --> Qdrant                      Vectors written to per-tenant collection

Nomic embed-text       --> Docker container            Runs as sidecar in offline bundle
                       --> Qdrant                      Same vector store, same schema, different source
                       --> No outbound network         Offline Docker Compose network policy

Hetzner Cloud          --> hcloud SDK                  Control plane provisions per-tenant VMs
                       --> Docker Compose / K3s        Per-tenant runtime on provisioned VMs
                       --> SOPS + age                  Per-tenant secrets decrypted at provision time
                       --> Prometheus                  Per-tenant metrics scraped from each VM

Docker Compose         --> All services containerized  MinIO, PostgreSQL, Qdrant, Redis, ClamAV, API
(offline mode)         --> No outbound network rules   Compose network with no external routes
                       --> Nomic container             Embeddings computed locally
                       --> Prometheus + Grafana        Optional local monitoring
```

---

## Installation (Python Dependencies)

```bash
# Core API + validation
pip install "fastapi>=0.115" "uvicorn[standard]>=0.30" "pydantic>=2.9" "pydantic-settings>=2.5"

# Database
pip install "sqlalchemy[asyncio]>=2.0" "asyncpg>=0.29" "alembic>=1.13"

# Task queue
pip install "celery[redis]>=5.4" "redis>=5.0"

# Object storage
pip install "boto3>=1.35"

# Vector store
pip install "qdrant-client>=1.12"

# HTTP client
pip install "httpx>=0.27"

# Security + auth
pip install "python-jose[cryptography]>=3.3" "cryptography>=43" "python-magic>=0.4.27"

# File handling
pip install "python-multipart>=0.0.9"

# Observability
pip install "structlog>=24.4" "prometheus-fastapi-instrumentator>=7.0"

# Resilience
pip install "tenacity>=9.0"

# Document parsing (DECIDED)
pip install "docling" "unstructured[all-docs]"

# Embeddings - offline (DECIDED)
pip install "nomic"

# Hetzner provisioning
pip install "hcloud>=2.2"
```

```bash
# Dev dependencies
pip install "pytest>=8.3" "pytest-asyncio>=0.24" "pytest-cov>=5.0" "ruff>=0.7" "mypy>=1.12" "pre-commit>=3.8"
```

---

## Docker Services Map (Offline Bundle)

```yaml
# docker-compose.offline.yml - service inventory
services:
  api:          # FastAPI application
  worker:       # Celery worker (document processing)
  beat:         # Celery beat (optional, for scheduled cleanup)
  postgres:     # PostgreSQL 16
  redis:        # Redis 7 (Celery broker)
  qdrant:       # Qdrant vector DB
  minio:        # MinIO object storage
  clamav:       # ClamAV malware scanner
  nomic:        # Nomic embed-text model server
  prometheus:   # Metrics (optional)
  grafana:      # Dashboards (optional)
```

---

## Version Verification Checklist

> **ACTION REQUIRED:** Before implementation, verify these versions against PyPI and official releases. All versions listed are from training data (May 2025 cutoff) and may be outdated.

| Package | Listed Version | Verify At | Confidence |
|---|---|---|---|
| fastapi | >=0.115 | https://pypi.org/project/fastapi/ | MEDIUM |
| uvicorn | >=0.30 | https://pypi.org/project/uvicorn/ | MEDIUM |
| pydantic | >=2.9 | https://pypi.org/project/pydantic/ | MEDIUM |
| sqlalchemy | >=2.0 | https://pypi.org/project/sqlalchemy/ | HIGH |
| asyncpg | >=0.29 | https://pypi.org/project/asyncpg/ | MEDIUM |
| alembic | >=1.13 | https://pypi.org/project/alembic/ | MEDIUM |
| celery | >=5.4 | https://pypi.org/project/celery/ | MEDIUM |
| redis (Python) | >=5.0 | https://pypi.org/project/redis/ | MEDIUM |
| boto3 | >=1.35 | https://pypi.org/project/boto3/ | MEDIUM |
| qdrant-client | >=1.12 | https://pypi.org/project/qdrant-client/ | MEDIUM |
| structlog | >=24.4 | https://pypi.org/project/structlog/ | MEDIUM |
| temporalio | >=1.7 | https://pypi.org/project/temporalio/ | LOW |
| httpx | >=0.27 | https://pypi.org/project/httpx/ | MEDIUM |
| hcloud | >=2.2 | https://pypi.org/project/hcloud/ | LOW |
| tenacity | >=9.0 | https://pypi.org/project/tenacity/ | MEDIUM |
| cryptography | >=43 | https://pypi.org/project/cryptography/ | MEDIUM |
| Qdrant server | >=1.12 | https://github.com/qdrant/qdrant/releases | MEDIUM |
| PostgreSQL | >=16 | https://www.postgresql.org/docs/release/ | HIGH |
| MinIO server | latest | https://github.com/minio/minio/releases | HIGH (rolling) |
| Redis server | >=7.4 | https://redis.io/downloads/ | MEDIUM |
| K3s | >=1.31 | https://github.com/k3s-io/k3s/releases | LOW |
| Prometheus | >=2.54 | https://github.com/prometheus/prometheus/releases | MEDIUM |
| Grafana | >=11 | https://grafana.com/grafana/download | MEDIUM |
| Loki | >=3.2 | https://github.com/grafana/loki/releases | MEDIUM |

---

## Sources

- FastAPI documentation: https://fastapi.tiangolo.com/ (HIGH confidence for architecture patterns)
- Qdrant documentation: https://qdrant.tech/documentation/ (HIGH confidence for multi-tenancy model)
- MinIO documentation: https://min.io/docs/ (HIGH confidence for S3 compatibility)
- PostgreSQL documentation: https://www.postgresql.org/docs/16/ (HIGH confidence for RLS, JSONB)
- Celery documentation: https://docs.celeryq.dev/ (HIGH confidence for task queue patterns)
- Temporal documentation: https://docs.temporal.io/ (MEDIUM confidence -- version not verified)
- structlog documentation: https://www.structlog.org/ (HIGH confidence for structured logging)
- Hetzner Cloud API: https://docs.hetzner.cloud/ (HIGH confidence -- locked-in)
- Docling documentation: https://docling-project.github.io/docling/ (HIGH confidence -- locked-in)
- Unstructured documentation: https://docs.unstructured.io/ (HIGH confidence -- locked-in)
- SOPS project: https://github.com/getsops/sops (HIGH confidence for secrets encryption)

> **Disclaimer:** Version numbers are from Claude's training data (cutoff May 2025). Architectural patterns and technology selection rationale are based on well-established ecosystem knowledge and carry HIGH confidence. Specific version numbers carry MEDIUM confidence and must be verified before use in implementation plans.
