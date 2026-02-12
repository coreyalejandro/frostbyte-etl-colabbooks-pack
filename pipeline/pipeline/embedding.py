"""
Text embedding service for multimodal pipeline.
Uses FROSTBYTE_EMBEDDING_ENDPOINT (OpenRouter-compatible) or Nomic local.
Reference: EMBEDDING_INDEXING_PLAN, TECH_DECISIONS (768d).
"""
from __future__ import annotations

import os

import httpx

EMBEDDING_ENDPOINT = os.getenv("FROSTBYTE_EMBEDDING_ENDPOINT", "http://localhost:8080/v1/embeddings")
EMBEDDING_DIM = 768


async def get_text_embedding(text: str) -> list[float]:
    """
    Get 768-d embedding for text. Calls OpenRouter-compatible API.
    Falls back to zero vector if endpoint unavailable (offline/stub).
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                EMBEDDING_ENDPOINT,
                json={
                    "model": "openai/text-embedding-3-small",
                    "input": [text],
                    "dimensions": EMBEDDING_DIM,
                },
            )
            r.raise_for_status()
            data = r.json()
            emb = data.get("data", [{}])[0].get("embedding", [])
            if len(emb) != EMBEDDING_DIM:
                return [0.0] * EMBEDDING_DIM  # fallback on dimension mismatch
            return emb
    except Exception:
        return [0.0] * EMBEDDING_DIM
