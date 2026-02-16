# Frostbyte ETL Planning Pack — Project Index

## Overview

Multi-tenant document ETL pipeline: intake → parse → policy → embed → store → serve. Dual mode (online/offline). Per-tenant isolation. Zero-shot implementation pack v1.0 (planning complete).

## Architecture

- **Control plane:** Tenant registry, provisioning, config (PostgreSQL `tenants` table)
- **Audit plane:** Append-only `audit_events` (PostgreSQL)
- **Data plane:** Per-tenant MinIO, PostgreSQL, Qdrant, Redis

## User Defined Namespaces

- [Leave blank — user populates]

## Components

- `specs/openapi.yaml` — OpenAPI 3.0.3 contract for documents, collections, health
- `pipeline/` — Python FastAPI app (1hr MVP + foundation + storage)
- `pipeline/routes/tenant_schemas.py` — PUT/GET/PATCH /tenants/{id}/schema (configurable schema extensions)
- `pipeline/tests/compliance/` — GDPR, HIPAA, FedRAMP test templates; run with FROSTBYTE_CONTROL_DB_URL
- `pipeline/config.py` — PlatformConfig from env (FROSTBYTE_*)
- `pipeline/db.py` — init_db, load_tenant_config, emit_audit_event
- `pipeline/secrets.py` — decrypt_tenant_secrets (SOPS + age)
- `pipeline/tenant.py` — create_tenant with audit emission
- `migrations/001_tenant_registry.sql` — tenants table
- `migrations/002_audit_events.sql` — audit_events table
- `scripts/run_migrations.sh` — Migration runner (001, 002, 005, 006, 007)
- `scripts/verify_e2e.sh` — E2E verification (Docker + ingest + verify)
- `pipeline/storage/` — MinIO, PostgreSQL, Qdrant, Redis provisioners; provision_tenant_storage; credentials + SOPS
- `pipeline/intake/` — Batch manifest validation; MIME/checksum/size; POST batch, GET batch, GET receipt; audit events; MinIO raw storage
- `pipeline/multimodal/` — Modality detection, image (OCR+CLIP), audio (Whisper), video (ffmpeg+frames) processors
- `pipeline/routes/collections.py` — POST /api/v1/collections/{name}/query with optional query_file (image/audio/video)
- `packages/admin-dashboard/` — React + TypeScript + Vite admin UI; Monochrome Machine design system (metal palette #0A0C0E–#E8EAED, amber #EAB308 accent only); IBM Plex Mono; top-bar nav [DASH] [TENANTS] [DOCS] [VERIFY] [CONTROL] [AUDIT]; milled panels (1px border, inset shadow, zero radius); Pipeline Schematic (ASCII DAG), Tenant Chambers, Document Queue ([↑][↓]), Verification Control Room (3 gates), Pipeline Control Panel, Audit Gallery, Inspector modal; Zustand+Immer; no Heroicons (ASCII/Unicode only)
- `scripts/run_multimodal_worker.py` — Redis multimodal:jobs consumer; inserts chunks, image_embeddings, video_frames; stores vectors in Qdrant
- `migrations/007_add_multimodal_support.sql` — documents, chunks (modality), image_embeddings (512d), video_frames; requires pgvector

## Implementation Order

Foundation → storage → intake ✅ → parsing → policy → embedding → serving (per HANDOFF.md).

## Key Docs

- `docs/product/PRD.md` — Product requirements
- `docs/reference/TECH_DECISIONS.md` — Component choices
- `docs/architecture/FOUNDATION_LAYER_PLAN.md` — Foundation implementation plan
- `docs/team/BRIEF_INTRO_ENTERPRISE_DATA_PIPELINES.md` — Brief intro to enterprise data pipelines (onboarding)
- `docs/team/ENGINEER_ONBOARDING.md` — Engineer onboarding (architecture, dev setup, first task)
- `BUILD_1HR.md` — Quick start
