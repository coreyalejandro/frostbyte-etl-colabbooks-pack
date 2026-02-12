"""
Rate limiting per INTAKE_GATEWAY_PLAN Section 2.1.
Redis key: tenant:{tenant_id}:ratelimit:ingest. 100 req/min per tenant.
"""
from __future__ import annotations

import asyncio
import os

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis

        url = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        _redis_client = redis.from_url(url)
    return _redis_client


async def check_rate_limit(
    tenant_id: str,
    limit: int = 100,
    window_sec: int = 60,
) -> None:
    """
    Increment and check rate limit. Raises 429 if exceeded.
    Uses Redis INCR + EXPIRE for sliding window.
    """
    key = f"tenant:{tenant_id}:ratelimit:ingest"

    def _check() -> bool:
        r = _get_redis()
        count = r.incr(key)
        if count == 1:
            r.expire(key, window_sec)
        return count <= limit

    ok = await asyncio.get_event_loop().run_in_executor(None, _check)
    if not ok:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": f"Limit {limit} req/{window_sec}s exceeded"},
        )
