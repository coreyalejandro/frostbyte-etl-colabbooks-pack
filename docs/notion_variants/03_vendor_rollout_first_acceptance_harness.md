# Colab Book 03 — Vendor Rollout-First ETL (Acceptance Harness & Self-Serve Fix Loops)

## Focus
Vendor success at scale: deterministic intake receipts, parse previews/diffs, and acceptance reports to reduce back-and-forth and support load.

## Pipeline contract (shared)
Document in → Structure out → Stored in DB + Vector  
Dual mode: Online API + Offline Docker (where applicable)

## Key emphasis areas
- Acceptance Harness
- Manifest Parity
- Parse Diff Reports
- Re-run Failed Segments

## Persona & journey anchor
Use `CUSTOMER_JOURNEY_MAP.md` as the canonical vendor-facing journey.  
Optimize for: first-pass vendor success, sovereignty confidence, and verifiable retrieval.

## Safety posture
Treat documents as untrusted inputs.  
Maintain strict separation between content and system/tool instructions.  
Require auditability across ingestion → normalization → embedding version → index writes → retrieval events.

## Diagrams
- Architecture: `diagrams/architecture.mmd`
- Tenancy: `diagrams/tenancy.mmd`
- Offline bundle: `diagrams/offline_bundle.mmd` (if relevant)

## Discussion prompts for Frode (practice)
1) What is the “minimum viable” acceptance harness for vendor rollout?
2) Which boundary is non-negotiable: offline-first, tenancy-first, or legal-grade citations?
3) What are the first three integration targets (DMS/email/API sources)?
4) What is the evaluation plan for retrieval quality and injection resistance?

## Sources
(see `docs/product/NOTION_EXPORT.md` or the notebook Sources section)
