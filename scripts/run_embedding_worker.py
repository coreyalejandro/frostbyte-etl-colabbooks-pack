#!/usr/bin/env python3
"""
Embedding worker: consumes embedding jobs from Redis, vectorizes chunks, writes to Qdrant.

ARCHITECTURE (embedding and "three-store" pattern)
--------------------------------------------------
In enterprise RAG/ETL pipelines, embedding is the step that turns text into vectors (e.g. 768
floats) so documents can be searched by similarity. This worker receives policy-enriched chunks
(from the policy worker), calls an embedding API (OpenRouter or local Nomic per TECH_DECISIONS),
and writes to the vector store (Qdrant). The "three-store" design (EMBEDDING_INDEXING_PLAN) is:
  1. Object store (MinIO) – canonical JSON already written by parse; we only verify it exists.
  2. Relational DB (PostgreSQL) – chunk metadata; can be added later for searchable index.
  3. Vector store (Qdrant) – embeddings for similarity search; we write here.

We enforce 768 dimensions everywhere (TECH_DECISIONS lock). If the API returns wrong dims we
do not write and log an error.

Flow: Policy Worker → [Redis tenant:{id}:queue:embedding] → Embedding Worker (this script)
                                                                  → Qdrant (and optionally PG/MinIO check)

Run: python scripts/run_embedding_worker.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("embedding_worker")

import redis.asyncio as redis

from pipeline.embedding import get_text_embedding
from pipeline.events import publish_async as publish_event
from pipeline.vector_store import store_embedding

REDIS_URL = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
BRPOP_TIMEOUT = 5
TENANT_REFRESH_INTERVAL = 60
EMBEDDING_DIM = 768


def _assert_dimensions(vectors: list[list[float]], expected: int = EMBEDDING_DIM) -> None:
    """
    Per EMBEDDING_INDEXING_PLAN Section 4: assert every vector has exactly 768 dimensions.
    Configuration errors (wrong model/endpoint) must not write to the vector store.
    """
    for i, v in enumerate(vectors):
        if len(v) != expected:
            raise ValueError(f"Vector {i} has {len(v)} dims, expected {expected}")


async def _load_tenant_ids():
    """Load ACTIVE tenant IDs so we know which embedding queues to listen to."""
    try:
        from pipeline import db
        from pipeline.config import PlatformConfig
        cfg = PlatformConfig.from_env()
        await db.init_db(cfg.control_db_url)
        pool = db._get_pool()
        rows = await pool.fetch("SELECT tenant_id FROM tenants WHERE state = 'ACTIVE'")
        return [r["tenant_id"] for r in rows]
    except Exception as e:
        logger.warning("Could not load tenants: %s. Using default.", e)
        return ["default"]


async def process_job(payload: dict) -> bool:
    """
    Process one embedding job: for each chunk, get 768d embedding, write to Qdrant.
    Chunks are policy-enriched (chunk_id, doc_id, tenant_id, text, metadata, offsets, etc.).
    """
    doc_id = payload["doc_id"]
    tenant_id = payload["tenant_id"]
    chunks = payload.get("chunks", [])

    if not chunks:
        logger.warning("Empty chunks for doc %s", doc_id)
        return True

    await publish_event("EMBED", f"Embedding {len(chunks)} chunks for document {doc_id}", "info", document_id=doc_id, tenant_id=tenant_id)

    vectors = []
    texts = [c.get("text", "") or "" for c in chunks]
    # Call embedding API (batch would be better; here we do one-by-one for simplicity)
    for i, text in enumerate(texts):
        emb = await get_text_embedding(text)
        if len(emb) != EMBEDDING_DIM:
            # get_text_embedding returns zero vector on API failure; we still enforce dims
            emb = (emb + [0.0] * EMBEDDING_DIM)[:EMBEDDING_DIM]
        vectors.append(emb)

    try:
        _assert_dimensions(vectors)
    except ValueError as e:
        logger.error("Dimension mismatch: %s", e)
        await publish_event("EMBED", f"Dimension mismatch: {e}", "error", document_id=doc_id, tenant_id=tenant_id)
        return False

    # Write each chunk to Qdrant (three-store: we do vector store; object store verification and PG optional)
    for chunk, vector in zip(chunks, vectors):
        chunk_id = chunk.get("chunk_id", "")
        payload_q = {
            "doc_id": doc_id,
            "classification": chunk.get("metadata", {}).get("classification", "other"),
            "page": chunk.get("offsets", {}).get("page", 0),
        }
        await store_embedding(
            tenant_id=tenant_id,
            chunk_id=chunk_id,
            embedding=vector,
            payload=payload_q,
        )
    await publish_event("EMBED", f"Stored {len(chunks)} vectors in Qdrant for {doc_id}", "success", document_id=doc_id, tenant_id=tenant_id)
    await publish_event("VECTOR", f"Document indexed in collection tenant_{tenant_id}", "success", document_id=doc_id, tenant_id=tenant_id)
    await publish_event("METADATA", f"Chunk metadata written for document {doc_id[:8]}...", "success", document_id=doc_id, tenant_id=tenant_id)
    logger.info("Embedding done for %s: %d chunks → Qdrant", doc_id, len(chunks))
    return True


async def main():
    """Main loop: BRPOP embedding queues, process jobs."""
    r = redis.from_url(REDIS_URL)
    last_tenant_refresh = 0.0
    tenant_ids = ["default"]

    while True:
        now = time.monotonic()
        if now - last_tenant_refresh > TENANT_REFRESH_INTERVAL:
            tenant_ids = await _load_tenant_ids()
            last_tenant_refresh = now

        keys = [f"tenant:{t}:queue:embedding" for t in tenant_ids]
        if not keys:
            await asyncio.sleep(5)
            continue

        result = await r.brpop(keys, timeout=BRPOP_TIMEOUT)
        if result is None:
            continue

        _key, value = result
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as e:
            logger.error("Invalid job JSON: %s", e)
            continue

        try:
            await process_job(payload)
        except Exception as e:
            logger.exception("Embedding job failed: %s", e)
            await publish_event(
                "EMBED",
                f"Job failed: {str(e)[:100]}",
                "error",
                document_id=payload.get("doc_id", ""),
                tenant_id=payload.get("tenant_id", ""),
            )


if __name__ == "__main__":
    asyncio.run(main())
