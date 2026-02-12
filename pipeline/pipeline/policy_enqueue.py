"""
Redis policy job enqueue per PARSING_PIPELINE_PLAN Section 9.
Key: tenant:{tenant_id}:queue:policy.
"""
from __future__ import annotations

import json
import os


def _get_redis():
    import redis

    url = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    return redis.from_url(url)


def enqueue_policy(
    *,
    doc_id: str,
    file_id: str,
    tenant_id: str,
    storage_path: str,
) -> None:
    """Push policy job to Redis list."""
    payload = {
        "doc_id": doc_id,
        "file_id": file_id,
        "tenant_id": tenant_id,
        "storage_path": storage_path,
    }
    r = _get_redis()
    key = f"tenant:{tenant_id}:queue:policy"
    r.lpush(key, json.dumps(payload))
