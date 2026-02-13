# AI, Law & Infrastructure — ETL Pipeline (Sovereignty + Safety)

## Purpose
A dual-mode ETL pipeline for vendor rollout:
- Online API mode (fast onboarding)
- Offline Docker mode (sovereignty / air-gapped)

Core contract: **document in → structure out → stored in DB + vector**

## Use for
- Regulated vendor onboarding (contracts/policies/SOPs/case files)
- RAG-ready corpora with provenance/audit requirements
- Tenant-isolated SaaS deployments

## Do not use for
- Legal citations without verifiable stored source slices
- Any workflow allowing untrusted docs to affect tool/system prompts
- Cross-tenant aggregation without explicit de-identification + permission

## Persona: Dana (Vendor Data Ops Lead)
Pain points:
- Ambiguous requirements
- Black-box parsing
- Sovereignty anxiety
- Retrieval mismatch
- Offline Docker fragility

## Journey map (summary)
Trust framing → onboarding → upload → parsing preview → enrichment gates → storage isolation → retrieval QA → ops deltas → incident containment

## Architecture (summary)
Vendor Sources → Intake Gateway → Docling+Unstructured → Canonical Structured Doc JSON → Policy Gates (PII/classification/injection defense) → Object Store + Relational DB + Vector Store → Serving APIs (RAG/agents/dashboards) → Audit/Observability

## Offline Docker mode (summary)
Compose bundle:
- parsers (Docling + Unstructured)
- local embeddings (Nomic)
- local DB + vector
- export artifacts (structured JSON + index snapshot + audit)

## Tooling
- Parsing: Docling, Unstructured
- Embeddings: OpenRouter (online), Nomic (offline)
- Infra isolation: Hetzner per-tenant environments
- Storage: object store + relational DB + vector store

## Safety controls (must-have)
- cite-only-from-retrieval
- deterministic chunk IDs + offsets
- immutable audit logs end-to-end
- strict tenant isolation (keys/storage/network)
- document injection defenses

## Vendor acceptance
Use the acceptance report template to provide:
- manifest parity, parse diffs, gate results, indexing results, required fixes

## Sources
- Frostbyte posture: https://frostbyteholding.com/
- Enterprise constraints: https://frostbyteholding.com/blog/stop-selling-toys-enterprise-solutions
- Security/injection framing: https://frostbyteholding.com/blog/ai-platform-security-nightmare
- Docling: https://docling-project.github.io/docling/reference/document_converter/
- Unstructured: https://docs.unstructured.io/open-source/introduction/overview
- OpenRouter embeddings: https://openrouter.ai/docs/api/reference/embeddings
- Hetzner API: https://docs.hetzner.cloud/reference/cloud
- Nomic embed: https://huggingface.co/nomic-ai/nomic-embed-text-v1
