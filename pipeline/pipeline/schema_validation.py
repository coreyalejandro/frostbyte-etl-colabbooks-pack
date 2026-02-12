"""
Validate custom_metadata against tenant schema (JSON Schema draft-07).
Reference: Enhancement #4 PRD - validation on POST /documents and POST /documents/{id}/chunks.
Call this when storing custom_metadata; raise HTTPException(422) on validation failure.
"""
from __future__ import annotations

from typing import Any

from jsonschema import validate


async def validate_custom_metadata(
    tenant_id: str,
    custom_metadata: dict[str, Any],
    schema_type: str,
) -> None:
    """
    Validate custom_metadata against the tenant's schema.
    Raises: jsonschema.ValidationError if invalid.
    schema_type: "document" or "chunk"
    """
    from . import db

    try:
        pool = db._get_pool()
    except RuntimeError:
        return  # DB not initialized; skip validation
    row = await pool.fetchrow("SELECT document_fields, chunk_fields FROM tenant_schemas WHERE tenant_id = $1", tenant_id)
    if not row:
        return  # No schema defined; allow empty or any
    schema = row["document_fields"] if schema_type == "document" else row["chunk_fields"]
    if not schema or not isinstance(schema, dict):
        return
    validate(instance=custom_metadata or {}, schema=schema)
