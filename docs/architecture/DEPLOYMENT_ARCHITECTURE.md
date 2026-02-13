# Deployment Architecture

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** DEPLOY-01 (online topology, runbook), DEPLOY-02 (offline Docker bundle)  
**References:** [TENANT_ISOLATION_HETZNER.md](TENANT_ISOLATION_HETZNER.md), [STORAGE_LAYER_PLAN.md](STORAGE_LAYER_PLAN.md), [FOUNDATION_LAYER_PLAN.md](FOUNDATION_LAYER_PLAN.md), [TECH_DECISIONS.md](TECH_DECISIONS.md)

---

## Document Conventions

| Notation | Meaning |
|----------|---------|
| `{tenant_id}` | Tenant identifier (lowercase, alphanumeric) |
| `cx22`, `cx32` | Hetzner server types (vCPU/RAM) |
| `nbg1` | Nuremberg location (default) |

---

## 1. Online Deployment: Hetzner Topology

### 1.1 Topology Overview

```
                                    ┌─────────────────────────────────────┐
                                    │           API Gateway (Traefik)      │
                                    │  TLS termination, routing, rate limit│
                                    └──────────────┬──────────────────────┘
                                                   │
        ┌──────────────────────────────────────────┼──────────────────────────────────────────┐
        │                                          │                                          │
        ▼                                          ▼                                          ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Tenant A      │  │ Tenant B      │  │ Tenant C      │  │ ...           │  │ Control Plane │
│ Data Plane    │  │ Data Plane    │  │ Data Plane    │  │               │  │ (shared)       │
├───────────────┤  ├───────────────┤  ├───────────────┤  └───────────────┘  ├───────────────┤
│ Gateway       │  │ Gateway       │  │ Gateway       │                     │ Tenant Registry│
│ Workers       │  │ Workers       │  │ Workers       │                     │ Provisioning   │
│ MinIO         │  │ MinIO         │  │ MinIO         │                     │ Audit Aggreg.  │
│ PostgreSQL    │  │ PostgreSQL    │  │ PostgreSQL    │                     └───────────────┘
│ Qdrant        │  │ Qdrant        │  │ Qdrant        │
│ Redis         │  │ Redis         │  │ Redis         │
└───────────────┘  └───────────────┘  └───────────────┘
```

Each tenant has a fully isolated data plane. The control plane is shared (tenant registry, provisioning orchestrator, audit stream aggregator). The API gateway (Traefik) routes by hostname: `{tenant_id}.pipeline.frostbyte.io`.

### 1.2 Server Types and Roles

| Role | server_type | vCPU | RAM | Purpose |
|------|-------------|------|-----|---------|
| gateway | cx22 | 2 | 4 GB | Intake API, serving API, auth |
| worker | cx22 | 2 | 4 GB | Parse, policy, embed workers (Celery) |
| db | cx22 (default) | 2 | 4 GB | Per-tenant PostgreSQL + Qdrant when small |
| db (heavy) | cx32 | 4 | 8 GB | Per-tenant PostgreSQL + Qdrant when large |

**Reference:** [TENANT_ISOLATION_HETZNER Section 2](TENANT_ISOLATION_HETZNER.md).

### 1.3 Network Layout

- **Per-tenant network:** `10.{tenant_octet}.0.0/16` with subnet `10.{tenant_octet}.1.0/24` in `eu-central`.
- **API gateway:** Public IP; routes HTTPS (443) to tenant gateways.
- **Bastion:** SSH (22) from control-plane bastion only.
- **Cross-tenant:** Denied by firewall (tenant A cannot reach tenant B CIDR).

**Reference:** [TENANT_ISOLATION_HETZNER Sections 3, 8](TENANT_ISOLATION_HETZNER.md).

### 1.4 Load Balancer (Traefik)

**Configuration (labels):**

```yaml
# Traefik dynamic config per tenant
http:
  routers:
    tenant-{tenant_id}:
      rule: "Host(`{tenant_id}.pipeline.frostbyte.io`)"
      service: tenant-{tenant_id}-gateway
      entryPoints:
        - websecure
  services:
    tenant-{tenant_id}-gateway:
      loadBalancer:
        servers:
          - url: "http://{gateway_private_ip}:8080"
        healthCheck:
          path: "/health"
          interval: "10s"
```

**Entry points:** `web` (80 redirect to 443), `websecure` (443 with TLS).

**Rate limiting:** 1000 req/min per tenant (configured via middleware).

**Reference:** TECH_DECISIONS Component #21 (Traefik v3).

### 1.5 Scaling Approach

- **Per-tenant scale-out:** Add worker VMs to a tenant when load increases.
- **Horizontal:** Same server type (cx22); scale workers via Celery concurrency or additional worker VMs.
- **Vertical:** Upgrade db role from cx22 to cx32 when tenant data grows.
- **No shared scaling:** Each tenant scales independently; no cross-tenant resource sharing.

### 1.6 High Availability Strategy

- **Tenant-level failover:** If a tenant's gateway fails, Traefik health check fails; remove from pool until recovered.
- **Control plane:** Single instance for v1; future: add replica for tenant registry (PostgreSQL streaming replication).
- **Per-tenant storage:** MinIO, PostgreSQL, Qdrant run as single instances per tenant for v1; HA (replication) is a future enhancement per tenant contract.
- **Kill-switch:** SUSPEND tenant state → 503 at gateway; no new jobs dispatched.

**Reference:** PRD Section 3 (tenant states, kill-switch).

---

## 2. Provisioning Runbook (Online)

### 2.1 Prerequisites

- Hetzner Cloud API token with create/delete permissions
- SSH key added to Hetzner project
- age key pair for tenant (SOPS secrets)
- DNS access for `{tenant_id}.pipeline.frostbyte.io` (Cloudflare, Route53, etc.)

### 2.2 Step Sequence

| Step | Action | API / Tool | Verification |
|------|--------|------------|--------------|
| 1 | Create tenant record (state=PENDING) | SQL INSERT | `SELECT * FROM tenants WHERE tenant_id = ?` |
| 2 | Create private network | `POST /networks` | `GET /networks/{id}` |
| 3 | Create firewall | `POST /firewalls` | `GET /firewalls/{id}` |
| 4 | Create gateway server | `POST /servers` | Poll until `status == "running"` |
| 5 | Create worker server(s) | `POST /servers` | Same |
| 6 | Create db server (if dedicated) | `POST /servers` | Same |
| 7 | Create and attach volume | `POST /volumes`, `POST /volumes/{id}/actions/attach` | `GET /volumes/{id}` |
| 8 | Apply firewall to servers | `POST /firewalls/{id}/actions/apply_to_resources` | Firewall rules active |
| 9 | Provision storage (MinIO, PostgreSQL, Qdrant, Redis) | STORAGE_LAYER_PLAN | Cross-store verification |
| 10 | Generate and encrypt secrets | SOPS + age | `sops --decrypt` succeeds |
| 11 | Create DNS record | External DNS API | `dig {tenant_id}.pipeline.frostbyte.io` |
| 12 | Deploy containers (Docker) | SSH + docker compose | `curl https://{tenant_id}.pipeline.frostbyte.io/health` → 200 |
| 13 | Update tenant (state=ACTIVE, endpoints) | SQL UPDATE | Registry updated |
| 14 | Emit TENANT_PROVISIONED | `emit_audit_event` | Audit log |

### 2.3 Rollback on Failure

If any step fails, roll back in reverse order:

1. Delete servers (detach volume first if attached)
2. Delete firewall
3. Delete network
4. Delete volume
5. Revert tenant state to FAILED
6. Emit audit event

**Reference:** [TENANT_ISOLATION_HETZNER Section 1](TENANT_ISOLATION_HETZNER.md) (Mermaid sequence diagram).

### 2.4 Runbook Script Outline

```bash
# frostbyte-provision-tenant.sh
# Usage: ./frostbyte-provision-tenant.sh <tenant_id> <tenant_octet>

set -e
TENANT_ID=$1
TENANT_OCTET=$2

# Validate inputs
# Create network, firewall, servers, volume (with rollback on failure)
# Call storage provisioning (minio, postgres, qdrant, redis)
# Generate secrets, encrypt with SOPS
# Create DNS record
# SSH to gateway, run docker compose
# Update tenant registry, emit audit
```

---

## 3. Offline Docker Bundle Specification

### 3.1 Bundle Structure

```
frostbyte-offline-bundle-v1.0/
├── MANIFEST.json           # Checksums, version, image list
├── docker-compose.yml      # Full stack
├── .env.example           # Template (no secrets)
├── config/
│   ├── tenant.json        # Single-tenant config
│   └── policy/            # Policy rules (optional)
├── models/
│   ├── nomic-embed-text-v1.5/  # GGUF or full weights
│   ├── clamav/            # main.cvd, daily.cvd, bytecode.cvd
│   └── pii/               # spaCy or Presidio model
├── images/                # Docker image tarballs
│   ├── postgres-16-alpine.tar
│   ├── redis-8-alpine.tar
│   ├── qdrant-v1.13.0.tar
│   ├── minio-latest.tar
│   ├── clamav-1.4.tar
│   ├── frostbyte-api-v1.0.tar
│   ├── frostbyte-worker-v1.0.tar
│   └── nomic-embed-v1.5.tar
├── scripts/
│   ├── install.sh         # Load images, create networks, start
│   ├── verify.sh          # Health checks, isolation tests
│   └── export.sh           # Export audit, backup
└── migrations/            # Alembic or SQL
    └── *.sql
```

### 3.2 docker-compose.yml Structure

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    # ... (from FOUNDATION_LAYER_PLAN)
    networks: [etl-internal]
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:8-alpine
    networks: [etl-internal]

  minio:
    image: minio/minio:latest
    command: server /data
    networks: [etl-internal]
    volumes: [miniodata:/data]

  qdrant:
    image: qdrant/qdrant:v1.13.0
    networks: [etl-internal]
    volumes: [qdrantdata:/qdrant/storage]

  clamav:
    image: clamav/clamav:1.4
    networks: [etl-internal]
    volumes: [clamavdata:/var/lib/clamav]

  nomic-embed:
    image: frostbyte/nomic-embed:v1.5  # Custom GPT4All-based
    networks: [etl-internal]
    volumes: [models:/models]

  intake-gateway:
    image: frostbyte/api:v1.0
    environment:
      FROSTBYTE_MODE: offline
      FROSTBYTE_EMBEDDING_ENDPOINT: http://nomic-embed:8080/embeddings
      # ... (from FOUNDATION_LAYER_PLAN env vars)
    networks: [etl-internal]
    ports: ["127.0.0.1:8080:8080"]
    depends_on: [postgres, redis, minio, clamav]

  celery-worker:
    image: frostbyte/worker:v1.0
    environment: # same as intake-gateway
    networks: [etl-internal]
    depends_on: [postgres, redis, minio, qdrant, nomic-embed]

  serving:
    image: frostbyte/api:v1.0
    # Same as intake; single binary with different entrypoint/config
    networks: [etl-internal]
    depends_on: [qdrant, postgres, minio]

networks:
  etl-internal:
    driver: bridge
    internal: true
    ipam:
      config:
        - subnet: 172.28.0.0/16

volumes:
  pgdata:
  miniodata:
  qdrantdata:
  clamavdata:
  models:
```

### 3.3 Image List (with Digest Pin Recommendation)

| Image | Tag | Digest Pin (example) | Purpose |
|-------|-----|---------------------|---------|
| postgres | 16-alpine | `@sha256:...` | Relational DB |
| redis | 8-alpine | `@sha256:...` | Broker, cache |
| qdrant/qdrant | v1.13.0 | `@sha256:...` | Vector store |
| minio/minio | latest | `@sha256:...` | Object store |
| clamav/clamav | 1.4 | `@sha256:...` | Malware scan |
| frostbyte/api | v1.0 | `@sha256:...` | API server |
| frostbyte/worker | v1.0 | `@sha256:...` | Celery worker |
| frostbyte/nomic-embed | v1.5 | `@sha256:...` | Local embeddings |

**Export:** `docker save -o images/{name}.tar {image}@sha256:{digest}`

### 3.4 Model Weights

| Model | Path in Bundle | Size | Checksum |
|-------|----------------|------|----------|
| Nomic embed-text v1.5 | models/nomic-embed-text-v1.5/model.gguf | ~275 MB (Q8_0) | SHA-256 in MANIFEST |
| ClamAV main.cvd | models/clamav/main.cvd | ~160 MB | SHA-256 |
| ClamAV daily.cvd | models/clamav/daily.cvd | ~120 MB | SHA-256 |
| ClamAV bytecode.cvd | models/clamav/bytecode.cvd | ~1 MB | SHA-256 |
| PII/NER (spaCy or Presidio) | models/pii/ | ~750 MB | SHA-256 |

**Reference:** TECH_DECISIONS Section 3.3, 3.4.

### 3.5 MANIFEST.json Schema

```json
{
  "version": "1.0",
  "bundle_id": "frostbyte-offline-2026-02-11",
  "created_at": "2026-02-11T12:00:00Z",
  "images": [
    {
      "name": "postgres:16-alpine",
      "file": "images/postgres-16-alpine.tar",
      "sha256": "...",
      "digest": "sha256:..."
    }
  ],
  "models": [
    {
      "name": "nomic-embed-text-v1.5",
      "path": "models/nomic-embed-text-v1.5/model.gguf",
      "sha256": "..."
    }
  ],
  "scripts": ["install.sh", "verify.sh", "export.sh"]
}
```

### 3.6 install.sh

```bash
#!/bin/bash
set -e
# 1. Load Docker images: for f in images/*.tar; do docker load -i "$f"; done
# 2. Create network: docker network create etl-internal (or use compose)
# 3. Copy models to volume mount path
# 4. docker compose up -d
# 5. Wait for health: curl -s http://127.0.0.1:8080/health | jq .status == "ok"
# 6. Run migrations: docker compose exec postgres psql -f /migrations/001_tenant_registry.sql
```

### 3.7 verify.sh

```bash
#!/bin/bash
set -e
# 1. docker network inspect etl-internal → "Internal": true
# 2. docker exec {container} ip route → no default route
# 3. docker exec {container} ping -c 1 8.8.8.8 → fail (expected)
# 4. curl -s http://127.0.0.1:8080/health → 200
# 5. Run smoke test: POST /api/v1/ingest (minimal batch), GET receipt
```

### 3.8 export.sh

```bash
#!/bin/bash
set -e
# 1. Export audit events: docker compose exec postgres psql -c "COPY (SELECT * FROM audit_events) TO STDOUT" > audit_export.jsonl
# 2. Optional: pg_dump tenant database
# 3. Optional: MinIO mc mirror for bucket backup
# 4. Create tarball of export with timestamp
```

---

## 4. Cross-References

| Topic | Document | Section |
|-------|----------|---------|
| Hetzner provisioning | TENANT_ISOLATION_HETZNER | 1, 2, 3, 4, 8 |
| Storage provisioning | STORAGE_LAYER_PLAN | All |
| Docker skeleton | FOUNDATION_LAYER_PLAN | 3 |
| Online/offline manifests | TECH_DECISIONS | 2, 3 |

---

## 5. Implementation Checklist

- [ ] Document Traefik dynamic config format for multi-tenant routing
- [ ] Implement provisioning runbook script (frostbyte-provision-tenant.sh)
- [ ] Build offline bundle export pipeline (images, models, scripts)
- [ ] Implement MANIFEST.json generation with checksums
- [ ] Test install.sh, verify.sh, export.sh on clean host
