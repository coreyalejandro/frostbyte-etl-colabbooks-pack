"""
Document list and chain-of-custody endpoints.
API-04: GET /api/v1/documents
API-06: GET /api/v1/documents/{id}/chain

DB column mapping:
  documents.custom_metadata  -> API field: metadata
  audit_events.event_type    -> API field: action
  audit_events.actor         -> API field: performed_by
  audit_events.details       -> API field: metadata (event metadata)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .. import db
from ..auth import get_tenant_from_token

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _get_pool():
    try:
        return db._get_pool()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "DB_UNAVAILABLE", "message": "Control-plane database not initialized"},
        ) from None


class DocumentItem(BaseModel):
    id: str
    tenant_id: str
    filename: str
    status: str
    modality: str
    metadata: dict[str, Any]   # mapped from custom_metadata
    created_at: datetime
    updated_at: datetime


class DocumentsListResponse(BaseModel):
    items: list[DocumentItem]
    total: int


class ChainEvent(BaseModel):
    action: str                 # mapped from event_type
    timestamp: datetime
    performed_by: str | None    # mapped from actor
    metadata: dict[str, Any]   # mapped from details


class ChainResponse(BaseModel):
    document_id: str
    events: list[ChainEvent]


def _row_to_document(row) -> DocumentItem:
    return DocumentItem(
        id=str(row["id"]),
        tenant_id=row["tenant_id"],
        filename=row["filename"],
        status=row["status"],
        modality=row["modality"],
        metadata=dict(row["custom_metadata"]) if row["custom_metadata"] else {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("", response_model=DocumentsListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    tenantId: str | None = Query(default=None),
    _: str | None = Depends(get_tenant_from_token),
) -> DocumentsListResponse:
    """List documents with optional tenant filter and pagination."""
    pool = _get_pool()
    offset = (page - 1) * limit

    # Single query: COUNT(*) OVER() avoids a second round-trip
    rows = await pool.fetch(
        """
        SELECT id, tenant_id, filename, status, modality,
               custom_metadata, created_at, updated_at,
               COUNT(*) OVER() AS total
        FROM documents
        WHERE ($1::text IS NULL OR tenant_id = $1)
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        tenantId,
        limit,
        offset,
    )

    total = int(rows[0]["total"]) if rows else 0
    return DocumentsListResponse(
        items=[_row_to_document(r) for r in rows],
        total=total,
    )


@router.get("/{document_id}/chain", response_model=ChainResponse)
async def get_document_chain(
    document_id: str,
    _: str | None = Depends(get_tenant_from_token),
) -> ChainResponse:
    """Return chain-of-custody audit events for a document."""
    pool = _get_pool()

    # Verify document exists first
    doc = await pool.fetchrow(
        "SELECT id FROM documents WHERE id = $1::uuid",
        document_id,
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "DOCUMENT_NOT_FOUND", "message": f"Document '{document_id}' not found"},
        )

    events = await pool.fetch(
        """
        SELECT event_id, event_type, timestamp, actor, details
        FROM audit_events
        WHERE resource_type = 'document' AND resource_id = $1
        ORDER BY timestamp ASC
        """,
        document_id,
    )

    return ChainResponse(
        document_id=document_id,
        events=[
            ChainEvent(
                action=row["event_type"],
                timestamp=row["timestamp"],
                performed_by=row["actor"],
                metadata=dict(row["details"]) if row["details"] else {},
            )
            for row in events
        ],
    )
