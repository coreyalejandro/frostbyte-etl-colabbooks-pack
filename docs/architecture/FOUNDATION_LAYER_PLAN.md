# Foundation Layer Implementation Plan

**Version:** 1.0  
**Created:** 2026-02-11  
**Requirement traceability:** IMPL-01  
**References:** [PRD.md](PRD.md) Section 3 (Tenant Lifecycle), Appendix G (Config Schema); [TENANT_ISOLATION_HETZNER.md](TENANT_ISOLATION_HETZNER.md) Section 1; [TENANT_ISOLATION_STORAGE_ENCRYPTION.md](TENANT_ISOLATION_STORAGE_ENCRYPTION.md) Section 6, Section 10; [AUDIT_ARCHITECTURE.md](AUDIT_ARCHITECTURE.md) Section 1, Section 2.3

---

## Document Conventions

| Notation | Meaning |
|---------|---------|
| `migrations/NNN_*.sql` | SQL migration files in version order |
| `{tenant_id}` | Tenant identifier (lowercase, alphanumeric) |
| Env var | Environment variable for platform configuration |

---

## 1. Tenant Data Model Schema

The tenant registry lives in the **control-plane PostgreSQL** (shared database), not in per-tenant databases. Per-tenant PostgreSQL databases hold tenant documents and chunks; the registry manages tenant lifecycle metadata and configuration.

**Cross-reference:** Tenant states and transition table — [PRD.md Section 3.1](PRD.md); Config schema — [PRD Appendix G](PRD.md).

### 1.1 Tenants Table DDL

Create migration `migrations/001_tenant_registry.sql`:

```sql
-- Tenant registry (control-plane database)
CREATE TABLE tenants (
  tenant_id                TEXT PRIMARY KEY,
  state                    TEXT NOT NULL CHECK (state IN (
    'PENDING', 'PROVISIONING', 'ACTIVE', 'SUSPENDED',
    'DEPROVISIONING', 'DEPROVISIONED', 'FAILED'
  )),
  config                   JSONB NOT NULL,
  config_version           INTEGER NOT NULL DEFAULT 1,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  provisioning_started_at  TIMESTAMPTZ,
  provisioned_at           TIMESTAMPTZ,
  age_public_key           TEXT,
  endpoints                JSONB
);

-- State transitions: PRD Section 3.1
COMMENT ON COLUMN tenants.state IS 'Tenant state machine; see PRD Section 3.1';
COMMENT ON COLUMN tenants.config IS 'Per-tenant configuration per PRD Appendix G';
COMMENT ON COLUMN tenants.config_version IS 'Incremented on every config change';
COMMENT ON COLUMN tenants.provisioning_started_at IS 'Set when state -> PROVISIONING';
COMMENT ON COLUMN tenants.provisioned_at IS 'Set when state -> ACTIVE';
COMMENT ON COLUMN tenants.age_public_key IS 'age public key for SOPS decryption; see TENANT_ISOLATION_STORAGE_ENCRYPTION Section 6';
COMMENT ON COLUMN tenants.endpoints IS 'JSON: {"api_url":"...","health_url":"..."}';

-- Indexes for common queries
CREATE INDEX idx_tenants_state ON tenants (state);
CREATE INDEX idx_tenants_created_at ON tenants (created_at);
CREATE INDEX idx_tenants_config ON tenants USING GIN (config);

-- Trigger to maintain updated_at
CREATE OR REPLACE FUNCTION tenants_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tenants_updated_at_trigger
  BEFORE UPDATE ON tenants
  FOR EACH ROW
  EXECUTE FUNCTION tenants_updated_at();
```

**Config JSONB shape (PRD Appendix G):**

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `pii_policy` | enum | Yes | `redact` |
| `pii_types` | array | Yes | `["SSN","DOB","EMAIL"]` |
| `classification_threshold` | number | No | 0.7 |
| `classification_review_enabled` | boolean | No | true |
| `injection_quarantine_threshold` | number | No | 0.7 |
| `injection_flag_threshold` | number | No | 0.3 |
| `max_file_size_mb` | number | No | 500 |
| `max_batch_size` | number | No | 1000 |
| `storage_quota_gb` | number | No | 100 |
| `embedding_mode` | enum | No | `online` |
| `embedding_dimensions` | number | No | 768 |
| `retrieval_top_k_max` | number | No | 50 |
| `retrieval_top_k_default` | number | No | 5 |
| `generation_enabled` | boolean | No | false |
| `generation_suppress_ungrounded` | boolean | No | true |
| `retention_days` | number | No | 2555 |
| `mime_allowlist` | array | No | Default allowlist |

See [PRD Appendix G](PRD.md) for full field descriptions and validation rules.

### 1.2 Migration File Path

- **Control-plane:** `migrations/001_tenant_registry.sql`
- **Execution order:** Run before any audit schema migrations (audit DDL references tenant lifecycle).

---

## 2. Configuration Framework

### 2.1 Environment Variables (Platform-Level)

| Variable | Purpose | Required | Example |
|----------|---------|----------|---------|
| `FROSTBYTE_MODE` | `online` or `offline` | Yes | `offline` |
| `FROSTBYTE_CONTROL_DB_URL` | Control-plane PostgreSQL connection string | Yes (online) | `postgresql://frostbyte:frostbyte@postgres:5432/frostbyte` |
| `FROSTBYTE_EMBEDDING_ENDPOINT` | External embedding API URL (online mode) | Yes (online) | `https://api.openai.com/v1/embeddings` |
| `FROSTBYTE_MINIO_ENDPOINT` | MinIO API endpoint | Yes | `http://minio:9000` |
| `FROSTBYTE_POSTGRES_HOST` | PostgreSQL host for per-tenant connections | Yes | `postgres` |
| `FROSTBYTE_QDRANT_URL` | Qdrant API URL | Yes | `http://qdrant:6333` |
| `FROSTBYTE_REDIS_URL` | Redis connection URL | Yes | `redis://redis:6379` |
| `FROSTBYTE_AUDIT_DB_URL` | Audit store URL (may equal control DB) | No | Same as control or SQLite path |
| `FROSTBYTE_SOPS_KEYS_PATH` | Base path for tenant age keys | Yes | `.secrets/tenants` |

**Loading:** On startup, load env vars into a `PlatformConfig` object. Validate required vars before accepting requests.

### 2.2 Tenant Configuration (Per-Tenant)

Tenant config is stored in `tenants.config` (JSONB). Load by tenant_id:

```python
def load_tenant_config(tenant_id: str) -> dict:
    row = db.execute(
        "SELECT config, config_version FROM tenants WHERE tenant_id = %s AND state = 'ACTIVE'",
        (tenant_id,)
    ).fetchone()
    if not row:
        raise TenantNotFound(tenant_id)
    return {"config": row[0], "config_version": row[1]}
```

**Validation:** Before insert/update, validate against PRD Appendix G schema. Reject invalid config; emit `TENANT_CONFIG_UPDATED` only on successful change.

### 2.3 Secrets (Per-Tenant, SOPS-Encrypted)

**Reference:** [TENANT_ISOLATION_STORAGE_ENCRYPTION.md Section 6](TENANT_ISOLATION_STORAGE_ENCRYPTION.md).

Secrets are stored in `.secrets/tenants/{tenant_id}/secrets.enc.yaml`, encrypted with the tenant's age key. The tenant's `age_public_key` is stored in the registry; the private key lives in `.secrets/tenants/{tenant_id}/key.age`.

**Decryption workflow (Section 6.5):**

```bash
export SOPS_AGE_KEY_FILE=.secrets/tenants/{tenant_id}/key.age
sops --decrypt .secrets/tenants/{tenant_id}/secrets.enc.yaml
```

** secrets file structure (before encryption):**

```yaml
minio_access_key: "tenant-{tenant_id}-access"
minio_secret_key: "{generated_secret}"
postgres_password: "{generated_password}"
qdrant_api_key: "{generated_key}"
redis_password: "{generated_password}"
tenant_api_key: "{generated_api_key}"
```

Application code must call `decrypt_tenant_secrets(tenant_id)` when provisioning a connection to a tenant's storage. Never log decrypted secrets.

### 2.4 Feature Flags

Feature flags can live in `tenants.config` JSONB. Examples:

- `generation_enabled` — whether answer generation is available (PRD Appendix G)
- `classification_review_enabled` — whether low-confidence docs go to review queue

No separate feature-flag table required for foundation layer. If a global feature-flag table is added later, it would be orthogonal to tenant config.

---

## 3. Docker Compose Skeleton

### 3.1 Existing Services (docker-compose.yml)

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| minio | minio/minio | 9000, 9001 | Object store |
| postgres | postgres:16-alpine | 5432 | Relational DB (control-plane + per-tenant in single instance for dev) |
| redis | redis:8-alpine | 6379 | Cache, queues |
| qdrant | qdrant/qdrant:v1.13.0 | 6333, 6334 | Vector store |

### 3.2 Control-Plane Schema Initialization

The shared `frostbyte` database holds:

1. **Tenant registry** — `tenants` table (migration 001)
2. **Audit events** — `audit_events` table (AUDIT_ARCHITECTURE Section 2.3)

**Migration order:**

1. `migrations/001_tenant_registry.sql` — tenants table
2. `migrations/002_audit_events.sql` — audit_events table (DDL from AUDIT_ARCHITECTURE Section 2.3)
3. Existing app migrations (e.g., 004_add_custom_metadata.sql) — per-tenant schema

**Startup sequence:**

```
1. docker compose up -d postgres minio redis qdrant
2. Wait for postgres healthcheck
3. Run migrations in order: 001, 002, then app migrations
4. Services ready for intake-gateway, parse-worker, etc.
```

### 3.3 Audit Events Table DDL (Reference)

**Reference:** [AUDIT_ARCHITECTURE.md Section 2.3](AUDIT_ARCHITECTURE.md).

Create `migrations/002_audit_events.sql`:

```sql
CREATE TABLE audit_events (
  event_id       UUID PRIMARY KEY,
  tenant_id      TEXT NOT NULL,
  event_type     TEXT NOT NULL,
  timestamp      TIMESTAMPTZ NOT NULL,
  actor          TEXT,
  resource_type  TEXT NOT NULL,
  resource_id    TEXT NOT NULL,
  details        JSONB NOT NULL,
  previous_event_id UUID REFERENCES audit_events(event_id)
);

CREATE INDEX idx_audit_tenant_timestamp ON audit_events (tenant_id, timestamp);
CREATE INDEX idx_audit_tenant_resource_timestamp ON audit_events (tenant_id, resource_id, timestamp);
CREATE INDEX idx_audit_event_type_timestamp ON audit_events (event_type, timestamp);
CREATE INDEX idx_audit_previous_event ON audit_events (previous_event_id) WHERE previous_event_id IS NOT NULL;

REVOKE UPDATE, DELETE ON audit_events FROM frostbyte_app;
GRANT INSERT, SELECT ON audit_events TO frostbyte_app;
GRANT SELECT ON audit_events TO frostbyte_auditor;

-- Optional: trigger to block UPDATE/DELETE
CREATE OR REPLACE FUNCTION block_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_events is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_events_no_update_delete
  BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW EXECUTE FUNCTION block_audit_modification();
```

(Note: PostgreSQL 16 uses `EXECUTE FUNCTION`; older versions use `EXECUTE PROCEDURE`.)

### 3.4 Offline Air-Gap Variant (Optional)

For offline mode, add an internal network to prevent outbound traffic:

```yaml
networks:
  internal:
    driver: bridge
    internal: true
```

Attach services to `internal` network. The host cannot reach embedding APIs; use local embedding container.

### 3.5 Service Placeholders (Skeleton)

The foundation layer does not require full pipeline services. For a runnable skeleton, optionally add stub services:

- `intake-gateway` — minimal HTTP server that reads tenant registry
- `celery-worker` — stub that connects to Redis

These are Phase 5–6 deliverables. The foundation layer only ensures the control-plane DB, tenant registry, and audit store are initialized.

---

## 4. Audit Event Emission

### 4.1 Event Schema Reference

**Reference:** [AUDIT_ARCHITECTURE.md Section 1](AUDIT_ARCHITECTURE.md).

| Field | Type | Required |
|-------|------|----------|
| `event_id` | UUID | Yes |
| `tenant_id` | TEXT | Yes |
| `event_type` | TEXT | Yes |
| `timestamp` | TIMESTAMPTZ | Yes |
| `actor` | TEXT | No |
| `resource_type` | TEXT | Yes |
| `resource_id` | TEXT | Yes |
| `details` | JSONB | Yes |
| `previous_event_id` | UUID | No |

### 4.2 Foundation-Layer Event Types

The foundation layer emits tenant lifecycle events only. Event types from [AUDIT_ARCHITECTURE Section 1.2](AUDIT_ARCHITECTURE.md):

| Event Type | Emitted When | resource_id |
|------------|--------------|-------------|
| `TENANT_CREATED` | create_tenant() processed | tenant_id |
| `TENANT_PROVISION_STARTED` | Provisioning initiated | tenant_id |
| `TENANT_PROVISIONED` | Provisioning completed (after storage verification) | tenant_id |
| `TENANT_CONFIG_UPDATED` | Configuration changed | tenant_id |

**Hash chain:** Tenant lifecycle events typically have `previous_event_id = null` (no document provenance chain).

### 4.3 Emission Pattern

Provide a shared function:

```python
def emit_audit_event(
    event_id: uuid.UUID,
    tenant_id: str,
    event_type: str,
    resource_type: str,
    resource_id: str,
    details: dict,
    actor: str = "system",
    previous_event_id: uuid.UUID | None = None,
) -> None:
    """Insert audit event. Idempotent on event_id (use ON CONFLICT DO NOTHING if needed)."""
    db.execute(
        """
        INSERT INTO audit_events (event_id, tenant_id, event_type, timestamp, actor, resource_type, resource_id, details, previous_event_id)
        VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s)
        """,
        (event_id, tenant_id, event_type, actor, resource_type, resource_id, json.dumps(details), previous_event_id),
    )
```

**Call sites:**

- `create_tenant()` → `emit_audit_event(..., event_type="TENANT_CREATED", resource_id=tenant_id)`
- `provision()` (start) → `emit_audit_event(..., event_type="TENANT_PROVISION_STARTED", resource_id=tenant_id)`
- `provisioning_completed()` (after Step 8 verification) → `emit_audit_event(..., event_type="TENANT_PROVISIONED", resource_id=tenant_id)`
- `update_config()` → `emit_audit_event(..., event_type="TENANT_CONFIG_UPDATED", resource_id=tenant_id, details={"changes": [...], "config_version": N, "previous_config_version": N-1})`

**Reference:** Combined provisioning sequence — [TENANT_ISOLATION_STORAGE_ENCRYPTION Section 10](TENANT_ISOLATION_STORAGE_ENCRYPTION.md); Provisioning flow — [TENANT_ISOLATION_HETZNER Section 1](TENANT_ISOLATION_HETZNER.md).

---

## 5. Cross-References Summary

| Topic | Document | Section |
|-------|----------|---------|
| Tenant states | PRD | Section 3.1 |
| Config schema | PRD | Appendix G |
| Audit event schema | AUDIT_ARCHITECTURE | Section 1 |
| Audit DDL | AUDIT_ARCHITECTURE | Section 2.3 |
| Secrets, SOPS | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 6 |
| Provisioning sequence (storage) | TENANT_ISOLATION_STORAGE_ENCRYPTION | Section 10 |
| Provisioning sequence (compute) | TENANT_ISOLATION_HETZNER | Section 1 |

---

## 6. Implementation Checklist

- [ ] Create `migrations/001_tenant_registry.sql` with tenants table DDL
- [ ] Create `migrations/002_audit_events.sql` with audit_events DDL
- [ ] Implement `PlatformConfig` loader from env vars
- [ ] Implement `load_tenant_config(tenant_id)` with JSONB fetch
- [ ] Implement `decrypt_tenant_secrets(tenant_id)` (SOPS + age)
- [ ] Implement `emit_audit_event(...)` and call from tenant lifecycle
- [ ] Document migration order in README or docker-compose docs
- [ ] Add startup script: wait for postgres → run migrations → signal ready
