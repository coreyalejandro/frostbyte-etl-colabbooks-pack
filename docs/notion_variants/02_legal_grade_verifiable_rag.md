# Colab Book 02 — Legal-Grade ETL for Verifiable RAG (Evidence & Citation Integrity)

## Focus
Legal-grade provenance: immutable source slices, retrieval proof objects, and citation validation gates to prevent 'fluent wrong' legal output.

## Pipeline contract (shared)
Document in → Structure out → Stored in DB + Vector  
Dual mode: Online API + Offline Docker (where applicable)

## Key emphasis areas
- Evidence Packaging Gate
- Retrieval Proof Gate
- Red-Team Gate
- Auditability

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
