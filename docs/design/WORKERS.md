# Pipeline Workers

This document explains the **worker** pattern used in the Frostbyte ETL pipeline and how to run each stage.

## What is a worker?

In enterprise pipelines, a **worker** is a process that:

- **Listens to a queue** (here, Redis lists) instead of serving HTTP
- **Processes one job at a time** (e.g. "parse this document", "run policy gates on this doc")
- **Enqueues the next stage** or writes to storage when done

Workers decouple stages: the API can accept uploads quickly and put work on a queue; workers consume at their own rate. You can run multiple workers for the same queue to scale horizontally.

## Pipeline flow (with queues)

```
[Intake API]  →  MinIO (raw file)
       ↓
[Parse Worker]   consumes  tenant:{id}:queue:parse
       ↓         writes   normalized/{tenant}/{doc}/structured.json
       ↓         enqueues tenant:{id}:queue:policy
[Policy Worker]  consumes  tenant:{id}:queue:policy
       ↓         runs     Gate 1 (PII) → Gate 2 (Classification) → Gate 3 (Injection)
       ↓         enqueues tenant:{id}:queue:embedding  (passing chunks only)
[Embedding Worker] consumes tenant:{id}:queue:embedding
       ↓         calls    Embedding API (768d)
       ↓         writes   Qdrant (vector store)
       →         (pipeline complete for that document)
```

## Scripts and how to run them

| Script | Queue(s) | Purpose |
|--------|----------|--------|
| `scripts/run_parse_worker.py` | `tenant:{id}:queue:parse` | Parse documents (Unstructured/Docling), write canonical JSON, enqueue policy |
| `scripts/run_policy_worker.py` | `tenant:{id}:queue:policy` | Run PII / classification / injection gates, enqueue embedding for passing chunks |
| `scripts/run_embedding_worker.py` | `tenant:{id}:queue:embedding` | Embed chunks (768d), write to Qdrant |
| `scripts/run_multimodal_worker.py` | `multimodal:jobs` | Process image/audio/video (OCR, Whisper, CLIP), write chunks and vectors |

**Prerequisites:** Docker stack up (`docker compose up -d`), migrations applied, Redis and MinIO and Qdrant reachable. For parse worker, Unstructured/Docling and MinIO are required. For embedding worker, `FROSTBYTE_EMBEDDING_ENDPOINT` can point to OpenRouter or a local Nomic endpoint; if unavailable, stub zero vectors are used.

**Run (each in its own terminal):**

```bash
# From repo root
cd pipeline && pip install -e .

# Terminal 1 – parse
python scripts/run_parse_worker.py

# Terminal 2 – policy
python scripts/run_policy_worker.py

# Terminal 3 – embedding
python scripts/run_embedding_worker.py

# Optional – multimodal (images/audio/video)
python scripts/run_multimodal_worker.py
```

## Where jobs come from

- **Parse queue:** Filled by the **batch intake** path: `POST /api/v1/ingest/{tenant_id}/batch` (manifest + files). The intake service validates files, writes to MinIO, and enqueues parse jobs. The **simple** `POST /api/v1/intake` (single file) does *not* enqueue parse; it does inline stub parse and optional multimodal queue.
- **Policy queue:** Filled only by the **parse worker** after it writes `normalized/{tenant}/{doc}/structured.json`.
- **Embedding queue:** Filled only by the **policy worker** with policy-enriched chunks that passed all gates.

So for the full pipeline (parse → policy → embedding), use the **batch intake** endpoint and run all three workers. The dashboard Pipeline Log will show live events from each stage when you have the pipeline API and workers running.

## References

- **Policy gates:** `docs/POLICY_ENGINE_PLAN.md`
- **Embedding and three-store:** `docs/EMBEDDING_INDEXING_PLAN.md`
- **Parsing:** `docs/PARSING_PIPELINE_PLAN.md`
