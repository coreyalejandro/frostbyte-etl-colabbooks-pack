"""
Redis parse job enqueue per INTAKE_GATEWAY_PLAN Section 6.
Key: tenant:{tenant_id}:queue:parse. Payload: file_id, batch_id, sha256, storage_path, tenant_id.
"""
from __future__ import annotations

import json
import os


def _get_redis():
    import redis

    url = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    return redis.from_url(url)


async def enqueue_parse(
    *,
    file_id: str,
    batch_id: str,
    sha256: str,
    storage_path: str,
    tenant_id: str,
    mime_type: str | None = None,
) -> None:
    """Push parse job to Redis list. Celery workers can BRPOP or similar."""
    import asyncio

    payload = {
        "file_id": file_id,
        "batch_id": batch_id,
        "sha256": sha256,
        "storage_path": storage_path,
        "tenant_id": tenant_id,
        "mime_type": mime_type,
    }

    def _push():
        r = _get_redis()
        key = f"tenant:{tenant_id}:queue:parse"
        r.lpush(key, json.dumps(payload))

    await asyncio.get_event_loop().run_in_executor(None, _push)
