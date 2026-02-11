# Phase 7: Deployment Architecture - Research

**Researched:** 2026-02-11
**Domain:** Online Hetzner deployment, offline Docker bundle, mode parity, offline update cycle
**Confidence:** HIGH (synthesized from TENANT_ISOLATION_HETZNER, STORAGE_LAYER_PLAN, FOUNDATION_LAYER_PLAN, TECH_DECISIONS, ARCHITECTURE)

## Summary

Phase 7 produces deployment specifications for both online (Hetzner Cloud) and offline (air-gapped Docker) modes. Requirements: DEPLOY-01 (online topology, runbook), DEPLOY-02 (offline Docker bundle), DEPLOY-03 (mode parity matrix), DEPLOY-04 (offline update cycle).

**Online:** TENANT_ISOLATION_HETZNER specifies server, network, firewall, volume provisioning. Deployment architecture adds: load balancer (Traefik), scaling approach (per-tenant VM scale-out), HA strategy (single-tenant isolation implies tenant-level failover), concrete runbook steps.

**Offline:** FOUNDATION_LAYER_PLAN and TECH_DECISIONS Section 3 define docker-compose skeleton and offline manifest. Deployment must specify: full compose structure (all pipeline services), image list with digests, model weights (Nomic v1.5, ClamAV signatures, PII model), config files, install/verify/export scripts.

**Mode parity:** TECH_DECISIONS Section 4 documents component compatibility and explicit divergences (embedding model, audit aggregation, ClamAV signatures, log aggregation). Phase 7 expands to every feature with online/offline status and workaround per divergence.

**Offline update cycle:** Signed bundles (SOPS/age or GPG), verification procedure (checksum + signature), migration steps (Alembic, schema changes), zero-downtime cutover (blue-green or rolling restart).

## Key References

- **TENANT_ISOLATION_HETZNER** — Provisioning sequence, Hetzner API, firewall rules, Docker offline equivalent
- **STORAGE_LAYER_PLAN** — MinIO, PostgreSQL, Qdrant, Redis provisioning
- **FOUNDATION_LAYER_PLAN** — Docker skeleton, migration order, env vars
- **TECH_DECISIONS** — Section 2 (online manifest), Section 3 (offline manifest), Section 4 (cross-mode)
- **INTAKE_GATEWAY_PLAN, PARSING_PIPELINE_PLAN, POLICY_ENGINE_PLAN, EMBEDDING_INDEXING_PLAN, SERVING_LAYER_PLAN** — Service definitions for compose
