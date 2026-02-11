# Phase 4: Foundation and Storage Layer - Research

**Researched:** 2026-02-11
**Domain:** Tenant data model, configuration framework, Docker skeleton, per-tenant storage provisioning
**Confidence:** HIGH (synthesized from PRD, TENANT_ISOLATION_*, AUDIT_ARCHITECTURE, ARCHITECTURE.md)

## Summary

Phase 4 produces two implementation plans: (1) Foundation layer — tenant registry schema, configuration framework (env vars, secrets, feature flags), Docker Compose skeleton, and audit event emission; (2) Storage layer — step-by-step MinIO, PostgreSQL, Qdrant, and Redis per-tenant provisioning with credential generation and isolation verification.

Both plans reference Phase 2 (TENANT_ISOLATION_HETZNER.md, TENANT_ISOLATION_STORAGE_ENCRYPTION.md) and Phase 3 (AUDIT_ARCHITECTURE.md) by specific section. The foundation layer defines the control-plane tenant registry used by all subsequent phases. The storage layer implements PRD 3.4 steps 4–7 and TENANT_ISOLATION_STORAGE_ENCRYPTION provisioning sequences.

**Primary recommendation:** Use a single control-plane database for the tenant registry (not per-tenant). Per-tenant PostgreSQL databases hold tenant data; the registry is shared. Config lives in tenant registry JSONB + env vars for mode (online/offline) + SOPS-encrypted secrets per tenant. Docker skeleton extends existing docker-compose.yml with audit store and optional pipeline services.

## Requirements Traceability

| Requirement | Phase 4 Plan | Content |
|-------------|--------------|---------|
| IMPL-01 | 04-01 | Tenant data model, config framework, Docker skeleton, audit emission |
| IMPL-02 | 04-02 | MinIO, PostgreSQL, Qdrant, Redis per-tenant provisioning |

## Key References

### Phase 2 (Isolation)

- **TENANT_ISOLATION_HETZNER.md** — Provisioning sequence (server, network, firewall, volume), PRD 3.4 steps 2–3, 5, 8–9
- **TENANT_ISOLATION_STORAGE_ENCRYPTION.md** — MinIO (Section 2), PostgreSQL (Section 3), Qdrant (Section 4), Redis (Section 5), SOPS+age (Section 6), provisioning sequence (Section 10)

### Phase 3 (Audit)

- **AUDIT_ARCHITECTURE.md** — Event schema (Section 1), immutable storage DDL (Section 2.3), event types (Section 1.2)

### PRD

- **Section 3** — Tenant states (7), transition table, provisioning steps 1–11, config schema (Appendix G)
- **Appendix G** — Tenant configuration JSON, config_version, TENANT_CONFIG_UPDATED audit event

## Tenant Data Model (Registry)

The tenant registry stores tenant metadata and configuration. It lives in the **control-plane PostgreSQL** (shared), not in per-tenant databases.

**Core fields:**
- `tenant_id` (TEXT PK)
- `state` (TEXT: PENDING, PROVISIONING, ACTIVE, SUSPENDED, DEPROVISIONING, DEPROVISIONED, FAILED)
- `config` (JSONB) — PRD Appendix G schema
- `config_version` (INT)
- `created_at`, `updated_at`
- `provisioning_started_at`, `provisioned_at` (nullable)
- `age_public_key` (TEXT, for SOPS decryption)
- `endpoints` (JSONB) — API URL, health URL

**Online vs offline:** Online mode uses dynamic provisioning; registry populated by orchestrator. Offline mode uses static config files; registry may be file-based or minimal DB.

## Configuration Framework

| Source | Purpose | Scope |
|--------|---------|-------|
| **Env vars** | Mode (online/offline), API URL, embedding endpoint, control-plane DB URL | Platform |
| **Tenant registry `config`** | Per-tenant policy (PII, classification, injection thresholds, mime_allowlist, etc.) | Per-tenant |
| **SOPS secrets** | Per-tenant credentials (DB, MinIO, Qdrant, Redis, API keys) | Per-tenant |
| **Feature flags** | Optional; can be in `config` (e.g., `generation_enabled`) | Per-tenant |

**Config loading:** Foundation layer provides a config loader that: (1) loads platform env, (2) fetches tenant config from registry by tenant_id, (3) resolves secrets from SOPS (decrypt with tenant's age key). Reference: TENANT_ISOLATION_STORAGE_ENCRYPTION Section 6.5.

## Docker Skeleton

**Existing:** docker-compose.yml has minio, postgres, redis, qdrant (single-tenant dev).

**Additions for foundation:**
- **Audit store:** Either (a) separate `audit` schema in control-plane Postgres, or (b) SQLite for offline. Per AUDIT_ARCHITECTURE Section 2.4.
- **Internal network:** Add `internal: true` network for offline air-gap mode variant.
- **Service placeholders:** intake-gateway, parse-worker, policy-engine, embedding-service, celery-worker (stub or minimal for skeleton).

**Skeleton purpose:** Engineer can `docker compose up` and have a runnable stack with tenant registry, storage, and audit store. Not full pipeline — that's Phase 5–6.

## Audit Event Emission (Foundation Layer)

Foundation layer emits:
- `TENANT_CREATED` — when tenant record created
- `TENANT_PROVISION_STARTED` — when provisioning begins
- `TENANT_PROVISIONED` — when provisioning completes (storage layer triggers this after verification)
- `TENANT_CONFIG_UPDATED` — when config changes

**Schema:** Per AUDIT_ARCHITECTURE Section 1. Events written to audit_events table (same DDL). Foundation layer does not emit document-level events; those are Phase 5–6.

## Storage Layer Execution Order

Per TENANT_ISOLATION_STORAGE_ENCRYPTION Section 10:
1. Generate age key pair
2. Generate credentials (passwords, keys)
3. Create SOPS-encrypted secrets file
4. Provision MinIO (bucket, IAM user, policy)
5. Provision PostgreSQL (database, user)
6. Provision Qdrant (collection)
7. Provision Redis (ACL user)
8. Run cross-store verification
9. Register in tenant registry (update endpoints, credentials ref)

## Sources

- docs/PRD.md (Section 3, Appendix G)
- docs/TENANT_ISOLATION_HETZNER.md
- docs/TENANT_ISOLATION_STORAGE_ENCRYPTION.md
- docs/AUDIT_ARCHITECTURE.md
- .planning/research/ARCHITECTURE.md
- docker-compose.yml (existing)

**Research date:** 2026-02-11
