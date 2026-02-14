"""
Tenant lifecycle operations.
Reference: docs/architecture/FOUNDATION_LAYER_PLAN.md Section 4, docs/product/PRD.md Section 3.
"""
from __future__ import annotations

import uuid
from typing import Any

from . import db


async def create_tenant(
    tenant_id: str,
    config: dict[str, Any],
) -> None:
    """
    Create a tenant in PENDING state and emit TENANT_CREATED.
    Reference: PRD Section 3.1, FOUNDATION_LAYER_PLAN Section 4.3.
    """
    pool = db._get_pool()  # noqa: SLF001
    event_id = uuid.uuid4()

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO tenants (tenant_id, state, config, config_version)
                VALUES ($1, 'PENDING', $2::jsonb, 1)
                ON CONFLICT (tenant_id) DO NOTHING
                """,
                tenant_id,
                config,
            )
            await db.emit_audit_event(
                event_id=event_id,
                tenant_id=tenant_id,
                event_type="TENANT_CREATED",
                resource_type="tenant",
                resource_id=tenant_id,
                details={"config_version": 1},
                actor="system",
                conn=conn,
            )
