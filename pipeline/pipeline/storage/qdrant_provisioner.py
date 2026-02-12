"""
Qdrant provisioning per STORAGE_LAYER_PLAN Section 4.
"""
from __future__ import annotations

import httpx

VECTOR_SIZE = 768
VECTOR_DISTANCE = "Cosine"


def get_collection_name(tenant_id: str) -> str:
    """Return Qdrant collection name for tenant. Per STORAGE_LAYER_PLAN 4.1."""
    return f"tenant_{tenant_id}"


def verify_tenant_access(tenant_id: str, collection_name: str) -> None:
    """Raise PermissionError if tenant cannot access collection. Per STORAGE_LAYER_PLAN 4.1."""
    expected = get_collection_name(tenant_id)
    if collection_name != expected:
        raise PermissionError(f"Tenant {tenant_id} cannot access {collection_name}")


async def provision_qdrant_collection(
    qdrant_url: str,
    tenant_id: str,
) -> None:
    """Create Qdrant collection for tenant. Per STORAGE_LAYER_PLAN 4.1."""
    coll = get_collection_name(tenant_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.put(
            f"{qdrant_url.rstrip('/')}/collections/{coll}",
            json={
                "vectors": {
                    "size": VECTOR_SIZE,
                    "distance": VECTOR_DISTANCE,
                },
            },
        )
        if r.status_code in (200, 201):
            return
        if r.status_code == 409:
            return  # already exists
        r.raise_for_status()


async def deprovision_qdrant_collection(qdrant_url: str, tenant_id: str) -> None:
    """Delete Qdrant collection. Per STORAGE_LAYER_PLAN 4.3."""
    coll = get_collection_name(tenant_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        await client.delete(f"{qdrant_url.rstrip('/')}/collections/{coll}")
