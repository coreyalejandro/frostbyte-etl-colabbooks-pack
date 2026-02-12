"""
Pipeline event publishing via Redis pub/sub.
Publishes structured events to channel 'pipeline:events' for SSE streaming
to the admin dashboard.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

REDIS_URL = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
CHANNEL = "pipeline:events"


def _build_event(
    stage: str,
    message: str,
    level: str = "info",
    document_id: str | None = None,
    tenant_id: str | None = None,
) -> str:
    """Build a JSON event payload."""
    event = {
        "stage": stage,
        "message": message,
        "level": level,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
    }
    if document_id:
        event["document_id"] = document_id
    if tenant_id:
        event["tenant_id"] = tenant_id
    return json.dumps(event)


# -- Sync publish (for workers running outside the event loop) --

_sync_client = None


def publish(
    stage: str,
    message: str,
    level: str = "info",
    document_id: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """Publish a pipeline event (sync). Safe to call from worker processes."""
    global _sync_client
    try:
        if _sync_client is None:
            import redis
            _sync_client = redis.from_url(REDIS_URL)
        payload = _build_event(stage, message, level, document_id, tenant_id)
        _sync_client.publish(CHANNEL, payload)
    except Exception:
        pass  # non-critical; don't break the pipeline if Redis pub/sub fails


# -- Async publish (for FastAPI handlers inside the event loop) --

_async_client = None


async def publish_async(
    stage: str,
    message: str,
    level: str = "info",
    document_id: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """Publish a pipeline event (async). Use from FastAPI route handlers."""
    global _async_client
    try:
        if _async_client is None:
            import redis.asyncio as aioredis
            _async_client = aioredis.from_url(REDIS_URL)
        payload = _build_event(stage, message, level, document_id, tenant_id)
        await _async_client.publish(CHANNEL, payload)
    except Exception:
        pass  # non-critical


async def publish_unimplemented_stages() -> None:
    """Emit informational messages for pipeline stages not yet wired to workers."""
    stages = [
        ("EVIDENCE", "Evidence packaging not yet wired -- will verify document integrity and chain of custody"),
        ("EMBED", "Embedding worker not yet active -- will vectorize chunks via Nomic/CLIP models"),
        ("VECTOR", "Vector store indexing pending -- will upsert embeddings to Qdrant collections"),
        ("METADATA", "Metadata indexer awaiting implementation -- will build searchable document index"),
        ("VERIFY", "Verification gate offline -- will run red-team and retrieval quality checks"),
    ]
    for stage, msg in stages:
        await publish_async(stage, msg, level="warn")
