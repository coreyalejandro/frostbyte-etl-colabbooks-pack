"""
Control-plane database operations.
Reference: docs/FOUNDATION_LAYER_PLAN.md Sections 2.2, 4.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg

# Module-level pool; initialized by init_db()
_pool: asyncpg.Pool | None = None


class TenantNotFoundError(Exception):
    """Raised when a tenant does not exist or is not ACTIVE."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        super().__init__(f"Tenant not found or not ACTIVE: {tenant_id}")


async def init_db(control_db_url: str, min_size: int = 2, max_size: int = 10) -> None:
    """Initialize the asyncpg connection pool for the control-plane database."""
    global _pool
    if _pool is not None:
        return
    _pool = await asyncpg.create_pool(
        control_db_url,
        min_size=min_size,
        max_size=max_size,
        command_timeout=60,
    )


async def close_db() -> None:
    """Close the database pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database not initialized; call init_db() first")
    return _pool


async def load_tenant_config(tenant_id: str) -> dict[str, Any]:
    """
    Load tenant configuration from the registry.
    Raises TenantNotFoundError if tenant does not exist or is not ACTIVE.
    Reference: FOUNDATION_LAYER_PLAN Section 2.2.
    """
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        SELECT config, config_version FROM tenants
        WHERE tenant_id = $1 AND state = 'ACTIVE'
        """,
        tenant_id,
    )
    if row is None:
        raise TenantNotFoundError(tenant_id)
    return {
        "config": dict(row["config"]) if row["config"] else {},
        "config_version": row["config_version"],
    }


async def emit_audit_event(
    *,
    event_id: uuid.UUID,
    tenant_id: str,
    event_type: str,
    resource_type: str,
    resource_id: str,
    details: dict[str, Any],
    actor: str = "system",
    previous_event_id: uuid.UUID | None = None,
    conn: asyncpg.Connection | None = None,
) -> None:
    """
    Insert an audit event. Idempotent on event_id (use ON CONFLICT DO NOTHING if needed).
    If conn is provided, use it (for transaction); otherwise use pool.
    Reference: FOUNDATION_LAYER_PLAN Section 4.3, AUDIT_ARCHITECTURE Section 1.
    """
    query = """
        INSERT INTO audit_events (
            event_id, tenant_id, event_type, timestamp, actor,
            resource_type, resource_id, details, previous_event_id
        )
        VALUES ($1, $2, $3, NOW(), $4, $5, $6, $7::jsonb, $8)
        ON CONFLICT (event_id) DO NOTHING
    """
    args = (event_id, tenant_id, event_type, actor, resource_type, resource_id, json.dumps(details), previous_event_id)
    if conn is not None:
        await conn.execute(query, *args)
    else:
        pool = _get_pool()
        await pool.execute(query, *args)
