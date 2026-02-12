"""
Tenant schema extension tests (Enhancement #4).
Verifies PUT/GET/PATCH /tenants/{tenant_id}/schema when control DB is available.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_put_get_schema(client, tenant_id, db):
    """PUT schema then GET returns same data."""
    schema = {
        "document_fields": {
            "type": "object",
            "properties": {"matter_number": {"type": "string", "pattern": "^M-[0-9]{6}$"}},
            "additionalProperties": False,
        },
        "chunk_fields": {},
    }
    put_resp = await client.put(f"/tenants/{tenant_id}/schema", json=schema)
    if put_resp.status_code == 503:
        pytest.skip("Control-plane DB not initialized (set FROSTBYTE_CONTROL_DB_URL)")
    assert put_resp.status_code == 200, f"PUT returned {put_resp.status_code}: {put_resp.text}"
    get_resp = await client.get(f"/tenants/{tenant_id}/schema")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["tenant_id"] == tenant_id
    assert "matter_number" in str(data.get("document_fields", {}))


@pytest.mark.asyncio
async def test_patch_schema(client, tenant_id):
    """PATCH merges new properties into existing schema (shallow merge at top level)."""
    await client.put(
        f"/tenants/{tenant_id}/schema",
        json={"document_fields": {"type": "object", "properties": {"a": {"type": "string"}}}, "chunk_fields": {}},
    )
    patch_resp = await client.patch(
        f"/tenants/{tenant_id}/schema",
        json={"document_fields": {"type": "object", "properties": {"b": {"type": "number"}}}},
    )
    if patch_resp.status_code == 503:
        pytest.skip("Control-plane DB not initialized (set FROSTBYTE_CONTROL_DB_URL)")
    assert patch_resp.status_code == 200, f"PATCH returned {patch_resp.status_code}: {patch_resp.text}"
    data = patch_resp.json()
    assert "b" in str(data.get("document_fields", {}))
