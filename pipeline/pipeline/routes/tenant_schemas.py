"""
Tenant-configurable schema extension API.
Reference: Enhancement #4 PRD - Configurable Schema Extensions
PUT/GET/PATCH /tenants/{tenant_id}/schema
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from .. import db
from ..schemas.tenant_schema import TenantSchema, TenantSchemaUpdate

router = APIRouter(prefix="/tenants", tags=["tenant-schemas"])


def _to_dict(val):
    """Convert jsonb/JSON value to Python dict."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val) if val else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _get_pool():
    try:
        return db._get_pool()
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "DB_UNAVAILABLE", "message": "Control-plane database not initialized"},
        ) from None


@router.put("/{tenant_id}/schema", response_model=TenantSchema)
async def put_schema(tenant_id: str, payload: TenantSchemaUpdate):
    """Set or replace the full schema for a tenant."""
    doc_fields = payload.document_fields if payload.document_fields is not None else {}
    chunk_fields = payload.chunk_fields if payload.chunk_fields is not None else {}

    if not isinstance(doc_fields, dict):
        raise HTTPException(422, detail={"error_code": "INVALID_SCHEMA", "message": "document_fields must be a JSON object"})
    if not isinstance(chunk_fields, dict):
        raise HTTPException(422, detail={"error_code": "INVALID_SCHEMA", "message": "chunk_fields must be a JSON object"})

    pool = _get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO tenant_schemas (tenant_id, document_fields, chunk_fields, updated_at)
        VALUES ($1, $2::jsonb, $3::jsonb, NOW())
        ON CONFLICT (tenant_id) DO UPDATE SET
            document_fields = EXCLUDED.document_fields,
            chunk_fields = EXCLUDED.chunk_fields,
            updated_at = EXCLUDED.updated_at
        RETURNING tenant_id, document_fields, chunk_fields, updated_at
        """,
        tenant_id,
        json.dumps(doc_fields),
        json.dumps(chunk_fields),
    )
    return TenantSchema(
        tenant_id=row["tenant_id"],
        document_fields=_to_dict(row["document_fields"]),
        chunk_fields=_to_dict(row["chunk_fields"]),
        updated_at=row["updated_at"],
    )


@router.get("/{tenant_id}/schema", response_model=TenantSchema)
async def get_schema(tenant_id: str):
    """Retrieve the current schema for a tenant."""
    pool = _get_pool()
    row = await pool.fetchrow("SELECT * FROM tenant_schemas WHERE tenant_id = $1", tenant_id)
    if not row:
        raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Schema not found for this tenant"})
    return TenantSchema(
        tenant_id=row["tenant_id"],
        document_fields=_to_dict(row["document_fields"]),
        chunk_fields=_to_dict(row["chunk_fields"]),
        updated_at=row["updated_at"],
    )


@router.patch("/{tenant_id}/schema", response_model=TenantSchema)
async def patch_schema(tenant_id: str, payload: TenantSchemaUpdate):
    """Add or update one or more properties in the schema (merge)."""
    if payload.document_fields is None and payload.chunk_fields is None:
        pool = _get_pool()
        row = await pool.fetchrow("SELECT * FROM tenant_schemas WHERE tenant_id = $1", tenant_id)
        if not row:
            raise HTTPException(404, detail={"error_code": "NOT_FOUND", "message": "Schema not found for this tenant"})
        return TenantSchema(
            tenant_id=row["tenant_id"],
            document_fields=_to_dict(row["document_fields"]),
            chunk_fields=_to_dict(row["chunk_fields"]),
            updated_at=row["updated_at"],
        )

    doc_fields = payload.document_fields if payload.document_fields is not None else {}
    chunk_fields = payload.chunk_fields if payload.chunk_fields is not None else {}
    if not isinstance(doc_fields, dict):
        raise HTTPException(422, detail={"error_code": "INVALID_SCHEMA", "message": "document_fields must be a JSON object"})
    if not isinstance(chunk_fields, dict):
        raise HTTPException(422, detail={"error_code": "INVALID_SCHEMA", "message": "chunk_fields must be a JSON object"})

    pool = _get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO tenant_schemas (tenant_id, document_fields, chunk_fields, updated_at)
        VALUES ($1, $2::jsonb, $3::jsonb, NOW())
        ON CONFLICT (tenant_id) DO UPDATE SET
            document_fields = tenant_schemas.document_fields || EXCLUDED.document_fields,
            chunk_fields = tenant_schemas.chunk_fields || EXCLUDED.chunk_fields,
            updated_at = NOW()
        RETURNING tenant_id, document_fields, chunk_fields, updated_at
        """,
        tenant_id,
        json.dumps(doc_fields),
        json.dumps(chunk_fields),
    )
    return TenantSchema(
        tenant_id=row["tenant_id"],
        document_fields=_to_dict(row["document_fields"]),
        chunk_fields=_to_dict(row["chunk_fields"]),
        updated_at=row["updated_at"],
    )
