"""
Pydantic models for tenant-configurable schema extensions.
Reference: Enhancement #4 PRD - Configurable Schema Extensions
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TenantSchema(BaseModel):
    """Full tenant schema as stored and returned by API."""

    tenant_id: str
    document_fields: dict[str, Any] = Field(default_factory=dict)
    chunk_fields: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


class TenantSchemaUpdate(BaseModel):
    """Request body for PUT/PATCH - document_fields and chunk_fields as JSON Schema."""

    document_fields: Optional[dict[str, Any]] = None
    chunk_fields: Optional[dict[str, Any]] = None
