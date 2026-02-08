# Frostbyte — AI, Law & Infrastructure ETL Pipeline (Share Pack)

This repo packages a **data-sovereign, safety-first ETL pipeline proposal** derived from Frode's pipeline sketch:
> “document in → structure out → stored in db and vector” with
> Unstructured + Docling, embeddings via OpenRouter (OpenAI/Qwen/Kimi), tenant isolation via Hetzner,
> and an offline Docker mode using Nomic embeddings.

## What’s inside

- `docs/ETL_PIPELINE_PROPOSAL.md` — Full proposal (use/do-not-use, phases, tools + alts)
- `docs/CUSTOMER_JOURNEY_MAP.md` — Persona + journey map with illustrated pain points
- `docs/THREAT_MODEL_SAFETY.md` — Security posture, injection defenses, auditability
- `diagrams/*.mmd` — Mermaid diagrams for architecture, tenancy, offline bundle
- `templates/VENDOR_ACCEPTANCE_REPORT.md` — Acceptance report template vendors can follow
- `docs/NOTION_EXPORT.md` — Single-page Notion-ready paste (same content, condensed)

## How to view diagrams

Paste the Mermaid files (`.mmd`) into any Mermaid renderer (GitHub supports Mermaid in Markdown in many contexts; Notion may require a Mermaid embed tool or screenshot export).

## Iteration workflow (practice loop)

1. Edit `docs/ETL_PIPELINE_PROPOSAL.md` with Frode’s feedback.
2. Update diagrams in `diagrams/`.
3. Regenerate the Notion page by copying `docs/NOTION_EXPORT.md`.

## Source links used (public)

- Frostbyte posture on enterprise/offline/audit: <https://frostbyteholding.com/>
- Frostbyte blog (enterprise constraints): <https://frostbyteholding.com/blog/stop-selling-toys-enterprise-solutions>
- Frostbyte blog (security/injection framing): <https://frostbyteholding.com/blog/ai-platform-security-nightmare>
- Docling docs: <https://docling-project.github.io/docling/reference/document_converter/>
- Unstructured OSS docs: <https://docs.unstructured.io/open-source/introduction/overview>
- OpenRouter embeddings API: <https://openrouter.ai/docs/api/reference/embeddings>
- Hetzner Cloud API: <https://docs.hetzner.cloud/reference/cloud>
- Nomic embed text model info: <https://huggingface.co/nomic-ai/nomic-embed-text-v1>

## Colab Books (one per verbalized sampling response)

These notebooks mirror the five proposal variants:

- `notebooks/01_baseline_dual_mode_sovereign_etl.ipynb`
- `notebooks/02_legal_grade_verifiable_rag.ipynb`
- `notebooks/03_vendor_rollout_first_acceptance_harness.ipynb`
- `notebooks/04_offline_first_airgapped_bundle.ipynb`
- `notebooks/05_multi_tenant_isolation_hetzner.ipynb`

## Notion-ready variants

- `docs/notion_variants/` contains one markdown page per variant for pasting into Notion.
