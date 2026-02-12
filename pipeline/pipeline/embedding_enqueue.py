"""
Redis embedding job enqueue per POLICY_ENGINE_PLAN Section 9, EMBEDDING_INDEXING_PLAN.
Key: tenant:{tenant_id}:queue:embedding.
"""
from __future__ import annotations

import json
import os
from typing import Any


def _get_redis():
    import redis

    url = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    return redis.from_url(url)


def enqueue_embedding(
    *,
    doc_id: str,
    file_id: str,
    tenant_id: str,
    storage_path: str,
    chunks: list[dict[str, Any]],
) -> None:
    """
    Push embedding job to Redis list.
    chunks: list of PolicyEnrichedChunk.model_dump() for passing chunks only.
    """
    payload = {
        "doc_id": doc_id,
        "file_id": file_id,
        "tenant_id": tenant_id,
        "storage_path": storage_path,
        "chunks": chunks,
    }
    r = _get_redis()
    key = f"tenant:{tenant_id}:queue:embedding"
    r.lpush(key, json.dumps(payload, default=str))
