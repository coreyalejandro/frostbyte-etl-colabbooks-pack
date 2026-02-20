"""
Tenant list and detail endpoints.
API-02: GET /api/v1/tenants
API-03: GET /api/v1/tenants/{id}

NOTE: tenants.tenant_id (TEXT) is aliased as both `id` and `name` in responses
until a dedicated `name` column is added via migration.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .. import db
from ..auth import get_tenant_from_token

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


def _get_pool():
    try:
        return db._get_pool()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "DB_UNAVAILABLE", "message": "Control-plane database not initialized"},
        ) from None


class TenantItem(BaseModel):
    id: str
    name: str          # alias for tenant_id until name column added
    state: str
    config: dict[str, Any]
    config_version: int
    created_at: datetime


class TenantsListResponse(BaseModel):
    items: list[TenantItem]
    total: int


def _row_to_tenant(row) -> TenantItem:
    return TenantItem(
        id=row["tenant_id"],
        name=row["tenant_id"],   # alias: name = tenant_id
        state=row["state"],
        config=dict(row["config"]) if row["config"] else {},
        config_version=row["config_version"],
        created_at=row["created_at"],
    )


@router.get("", response_model=TenantsListResponse)
async def list_tenants(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _: str | None = Depends(get_tenant_from_token),
) -> TenantsListResponse:
    """List all tenants with pagination."""
    pool = _get_pool()
    offset = (page - 1) * limit

    rows = await pool.fetch(
        """
        SELECT tenant_id, state, config, config_version, created_at
        FROM tenants
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit,
        offset,
    )
    total = await pool.fetchval("SELECT COUNT(*) FROM tenants")

    return TenantsListResponse(
        items=[_row_to_tenant(r) for r in rows],
        total=total or 0,
    )


@router.get("/{tenant_id}", response_model=TenantItem)
async def get_tenant(
    tenant_id: str,
    _: str | None = Depends(get_tenant_from_token),
) -> TenantItem:
    """Get a single tenant by ID."""
    pool = _get_pool()
    row = await pool.fetchrow(
        """
        SELECT tenant_id, state, config, config_version, created_at
        FROM tenants
        WHERE tenant_id = $1
        """,
        tenant_id,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "TENANT_NOT_FOUND", "message": f"Tenant '{tenant_id}' not found"},
        )
    return _row_to_tenant(row)
