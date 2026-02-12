"""
Vector store abstraction for multimodal pipeline.
Stores embeddings in Qdrant. Supports 768d (text) and 512d (CLIP) collections.
Reference: Enhancement #9 PRD.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

QDRANT_URL = os.getenv("QDRANT_URL", os.getenv("FROSTBYTE_QDRANT_URL", "http://localhost:6333"))
TEXT_DIM = 768
IMAGE_DIM = 512

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client


def _point_id_from_chunk(chunk_id: str) -> int:
    """Derive numeric ID for Qdrant from chunk_id string."""
    return int(hashlib.sha256(chunk_id.encode()).hexdigest()[:15], 16) % (2**63)


async def store_embedding(
    *,
    tenant_id: str,
    chunk_id: str,
    embedding: list[float],
    payload: dict[str, Any],
    collection_suffix: str | None = None,
) -> None:
    """
    Store embedding in Qdrant. Uses tenant_{id} for text (768d) or tenant_{id}_images for CLIP (512d).
    """
    client = _get_client()
    dim = len(embedding)
    if collection_suffix is None:
        collection_suffix = "_images" if dim == IMAGE_DIM else ""
    coll = f"tenant_{tenant_id}{collection_suffix}"

    try:
        client.get_collection(coll)
    except Exception:
        vec_size = IMAGE_DIM if dim == IMAGE_DIM else TEXT_DIM
        client.create_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=vec_size, distance=Distance.COSINE),
        )

    point_id = _point_id_from_chunk(chunk_id)
    payload["chunk_id"] = chunk_id
    payload["tenant_id"] = tenant_id

    client.upsert(
        collection_name=coll,
        points=[PointStruct(id=point_id, vector=embedding, payload=payload)],
    )


async def search_qdrant(
    *,
    tenant_id: str,
    vector: list[float],
    top_k: int = 10,
    collection_suffix: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search Qdrant by vector. Uses tenant_{id} or tenant_{id}_images for 512d.
    """
    client = _get_client()
    dim = len(vector)
    if collection_suffix is None:
        collection_suffix = "_images" if dim == IMAGE_DIM else ""
    coll = f"tenant_{tenant_id}{collection_suffix}"

    try:
        results, _ = client.search(
            collection_name=coll,
            query_vector=vector,
            limit=top_k,
        )
        return [
            {
                "chunk_id": h.payload.get("chunk_id"),
                "score": h.score,
                "document_id": h.payload.get("document_id"),
                "content": h.payload.get("content", ""),
                **{k: v for k, v in h.payload.items() if k not in ("chunk_id", "document_id", "content")},
            }
            for h in results
        ]
    except Exception:
        return []
