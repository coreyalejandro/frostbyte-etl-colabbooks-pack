---
phase: 01-product-definition-and-tech-decisions
plan: 02
subsystem: infra
tags: [fastapi, postgresql, qdrant, minio, celery, redis, docling, unstructured, nomic, openrouter, docker, prometheus, grafana, structlog, traefik, sops, clamav]

# Dependency graph
requires:
  - phase: 01-product-definition-and-tech-decisions
    provides: "Phase 1 research with verified version pins and resolved open questions (01-RESEARCH.md)"
provides:
  - "Complete component decision table with 35 locked-in technology choices (TECH-01)"
  - "Online mode dependency manifest with Python packages, Docker images, and ML model spec (TECH-02)"
  - "Offline mode dependency manifest with local model weights, ClamAV signatures, Docker tarballs, and bundle size estimate (TECH-03)"
  - "Cross-mode compatibility matrix with 4 explicit divergences"
  - "Version pin update procedure for ongoing maintenance"
affects: [02-tenant-isolation-architecture, 03-audit-stream-and-document-safety, 04-foundation-and-storage-layer, 05-intake-and-parsing-pipeline, 06-policy-embedding-and-serving, 07-deployment-architecture, 08-team-readiness-documentation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Locked-in vs Selected decision taxonomy", "Version floor pinning with verified sources", "Strict superset pattern for offline manifest", "Cross-mode compatibility matrix with explicit divergences"]

key-files:
  created:
    - "docs/TECH_DECISIONS.md"
  modified: []

key-decisions:
  - "MinIO: continue despite maintenance mode (Option A); Garage documented as migration target"
  - "Embedding dimensions: 768d locked for both online (OpenRouter text-embedding-3-small with dimensions=768) and offline (Nomic embed-text v1.5 native 768d)"
  - "Nomic: lock to v1.5; v2 MoE local inference not yet confirmed"
  - "Qdrant: collection-per-tenant for isolation-by-construction; tiered multitenancy rejected for regulated tenants"
  - "Celery + Redis over Temporal for initial implementation (lower operational complexity)"
  - "SOPS + age over Vault for secrets management at <20 tenants"
  - "Traefik over Caddy for API gateway (stronger Docker integration)"

patterns-established:
  - "Decision table format: Component | Technology | Version Pin | Rationale | Alternatives Rejected | Why Rejected"
  - "Version floor sourcing: 01-RESEARCH.md verified pins override STACK.md estimates"
  - "Offline manifest = strict superset of online manifest"
  - "Cross-mode compatibility documented per component with transferability assessment"

# Metrics
duration: 12min
completed: 2026-02-08
---

# Plan 01-02: Technology Decisions Summary

**35 component decisions locked with version-pinned dependency manifests for online and offline modes, cross-mode compatibility matrix, and MinIO maintenance-mode acknowledgment with Garage migration path**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-08
- **Completed:** 2026-02-08
- **Tasks:** 2
- **Files created:** 1

## Accomplishments

- Created `docs/TECH_DECISIONS.md` with 5 sections: document conventions, component decision table (35 components), online dependency manifest, offline dependency manifest, cross-mode compatibility matrix, and version pin update procedure
- Resolved all 4 open questions from 01-RESEARCH.md: MinIO maintenance mode, embedding dimension alignment, Nomic v1.5 vs v2, Qdrant collection-per-tenant vs tiered multitenancy
- Eliminated all ambiguous language ("choose between", "consider", "evaluate") from technology decisions
- Documented 4 explicit divergences between online and offline modes with impact assessments
- Estimated offline bundle size at ~5-7 GB with component-level breakdown

## Task Commits

Each task was committed atomically:

1. **Task 1: Write component decision table (TECH-01)** - `a914653` (feat)
2. **Task 2: Write dependency manifests and compatibility matrix (TECH-02, TECH-03)** - `d5b91d0` (feat)

## Files Created/Modified

- `docs/TECH_DECISIONS.md` - Complete technology decisions document covering TECH-01, TECH-02, and TECH-03 requirements. Contains: document conventions, 35-component decision table (7 locked-in + 28 selected), 4 resolved open questions, online dependency manifest (Python packages in pyproject.toml format + Docker images + ML model), offline dependency manifest (superset with local model weights, ClamAV signatures, Docker tarballs, bundle size estimate), cross-mode compatibility matrix (16 components with transferability notes + 4 explicit divergences), and version pin update procedure.

## Decisions Made

1. **MinIO maintenance mode (Option A):** Continue with MinIO. The S3 API is stable, the codebase is mature, all code uses boto3 (zero-code-change migration). Garage documented as migration target if MinIO is abandoned.

2. **Embedding dimensions (768d both modes):** Online uses OpenRouter text-embedding-3-small with `dimensions=768` parameter. Offline uses Nomic embed-text v1.5 at native 768d. Cross-mode vector compatibility enabled by construction.

3. **Nomic v1.5 (locked):** v2 MoE local inference not yet confirmed via Ollama. v1.5 is production-ready for local inference via GPT4All. v2 documented as future upgrade path requiring full re-indexing.

4. **Qdrant collection-per-tenant:** Tiered multitenancy (Qdrant 1.16) rejected for regulated tenants. Shared shards violate isolation-by-construction. Collection-per-tenant provides structural isolation with no query path to another tenant's vectors.

5. **Traefik selected over Caddy:** Stronger Docker integration and more mature load-balancing. Caddy acknowledged as viable alternative.

6. **Version floors raised per 01-RESEARCH.md:** Pydantic >=2.10, SQLAlchemy >=2.0.46, Celery >=5.6, Redis >=8.0, Qdrant >=1.13, structlog >=25.1, Prometheus >=3.5, hcloud >=2.10.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. This plan produces a planning document, not runnable code.

## Next Phase Readiness

- Technology decisions are locked. All subsequent phases (2-8) reference `docs/TECH_DECISIONS.md` for tool selections and version pins.
- Plan 01-01 (PRD) should be completed to provide the product specification that pairs with these technology decisions.
- Phase 2 (Tenant Isolation Architecture) can proceed with concrete technology choices for Hetzner provisioning, storage namespaces, and encryption.
- Phase 4 (Foundation and Storage Layer) can reference the dependency manifest directly for `pyproject.toml` and `docker-compose.yml` assembly.
- Phase 7 (Deployment Architecture) can reference the cross-mode compatibility matrix for mode parity documentation.

---
*Phase: 01-product-definition-and-tech-decisions*
*Completed: 2026-02-08*
