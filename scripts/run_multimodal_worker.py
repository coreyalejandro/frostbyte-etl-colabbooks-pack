#!/usr/bin/env python3
"""
Multimodal worker: consumes from Redis multimodal:jobs, processes images/audio/video.
Reference: Enhancement #9 PRD.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import uuid

import asyncpg
import redis.asyncio as redis
from pgvector.asyncpg import register_vector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multimodal_worker")

# Add pipeline to path
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.events import publish_async as publish_event

REDIS_URL = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
DATABASE_URL = os.getenv("FROSTBYTE_CONTROL_DB_URL", os.getenv("POSTGRES_URL", "postgresql://frostbyte:frostbyte@localhost:5432/frostbyte")).replace("+asyncpg", "")


async def run_worker() -> None:
    r = redis.from_url(REDIS_URL)
    while True:
        try:
            result = await r.blpop("multimodal:jobs", timeout=1)
            if not result:
                continue
            _key, payload_bytes = result
            data = json.loads(payload_bytes)
            job_id = data["job_id"]
            document_id = data["document_id"]
            tenant_id = data["tenant_id"]
            filename = data["filename"]
            content = base64.b64decode(data["content"])

            from pipeline.multimodal import detect_modality
            from pipeline.multimodal.image_processor import process_image
            from pipeline.multimodal.audio_processor import process_audio
            from pipeline.multimodal.video_processor import process_video
            from pipeline.embedding import get_text_embedding
            from pipeline.vector_store import store_embedding

            modality = detect_modality(filename)
            await publish_event("INTAKE", f"Multimodal worker processing: {filename} ({modality})", "info", document_id=document_id, tenant_id=tenant_id)
            conn = await asyncpg.connect(DATABASE_URL)
            await register_vector(conn)

            try:
                if modality == "image":
                    await publish_event("PARSE", f"Running OCR + CLIP on image: {filename}", "info", document_id=document_id, tenant_id=tenant_id)
                    result_data = await process_image(content, filename)
                    text_chunk_id = str(uuid.uuid4())
                    text_embedding = await get_text_embedding(result_data["ocr_text"])
                    await conn.execute(
                        """
                        INSERT INTO chunks (chunk_id, document_id, content, embedding, modality, created_at)
                        VALUES ($1, $2, $3, $4, $5, now())
                        """,
                        text_chunk_id,
                        uuid.UUID(document_id),
                        result_data["ocr_text"],
                        text_embedding if text_embedding else [0.0] * 768,
                        "image_text",
                    )
                    image_chunk_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO chunks (chunk_id, document_id, content, modality, created_at)
                        VALUES ($1, $2, $3, $4, now())
                        """,
                        image_chunk_id,
                        uuid.UUID(document_id),
                        "[image embedding]",
                        "image_embedding",
                    )
                    await conn.execute(
                        """
                        INSERT INTO image_embeddings (chunk_id, embedding)
                        VALUES ($1, $2)
                        """,
                        uuid.UUID(image_chunk_id),
                        result_data["embedding"] if result_data["embedding"] else [0.0] * 512,
                    )
                    await store_embedding(
                        tenant_id=tenant_id,
                        chunk_id=image_chunk_id,
                        embedding=result_data["embedding"],
                        payload={"modality": "image", "document_id": document_id},
                    )

                elif modality == "audio":
                    await publish_event("PARSE", f"Running Whisper transcription on audio: {filename}", "info", document_id=document_id, tenant_id=tenant_id)
                    result_data = await process_audio(content, filename)
                    transcript = result_data["transcript"]
                    embedding = await get_text_embedding(transcript)
                    chunk_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO chunks (chunk_id, document_id, content, embedding, modality, created_at)
                        VALUES ($1, $2, $3, $4, $5, now())
                        """,
                        chunk_id,
                        uuid.UUID(document_id),
                        transcript,
                        embedding,
                        "audio_transcript",
                    )
                    await store_embedding(
                        tenant_id=tenant_id,
                        chunk_id=chunk_id,
                        embedding=embedding,
                        payload={"modality": "audio", "document_id": document_id},
                    )

                elif modality == "video":
                    await publish_event("PARSE", f"Extracting audio + frames from video: {filename}", "info", document_id=document_id, tenant_id=tenant_id)
                    result_data = await process_video(content, filename)
                    transcript = result_data["transcript"]
                    embedding = await get_text_embedding(transcript)
                    chunk_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        INSERT INTO chunks (chunk_id, document_id, content, embedding, modality, created_at)
                        VALUES ($1, $2, $3, $4, $5, now())
                        """,
                        chunk_id,
                        uuid.UUID(document_id),
                        transcript,
                        embedding,
                        "video_transcript",
                    )
                    await store_embedding(
                        tenant_id=tenant_id,
                        chunk_id=chunk_id,
                        embedding=embedding,
                        payload={"modality": "video_transcript", "document_id": document_id},
                    )
                    for frame in result_data["frames"]:
                        if frame["ocr_text"].strip():
                            frame_text_chunk = str(uuid.uuid4())
                            text_emb = await get_text_embedding(frame["ocr_text"])
                            await conn.execute(
                                """
                                INSERT INTO chunks (chunk_id, document_id, content, embedding, modality, created_at)
                                VALUES ($1, $2, $3, $4, $5, now())
                                """,
                                frame_text_chunk,
                                uuid.UUID(document_id),
                                frame["ocr_text"],
                                text_emb,
                                "video_frame_text",
                            )
                            await store_embedding(
                                tenant_id=tenant_id,
                                chunk_id=frame_text_chunk,
                                embedding=text_emb,
                                payload={"modality": "video_frame_text", "document_id": document_id, "timestamp": frame["timestamp"]},
                            )
                        frame_embed_chunk = str(uuid.uuid4())
                        await conn.execute(
                            """
                            INSERT INTO chunks (chunk_id, document_id, content, modality, created_at)
                            VALUES ($1, $2, $3, $4, now())
                            """,
                            frame_embed_chunk,
                            uuid.UUID(document_id),
                            "[frame embedding]",
                            "video_frame_embedding",
                        )
                        await conn.execute(
                            """
                            INSERT INTO image_embeddings (chunk_id, embedding)
                            VALUES ($1, $2)
                            """,
                            uuid.UUID(frame_embed_chunk),
                            frame["embedding"],
                        )
                        await conn.execute(
                            """
                            INSERT INTO video_frames (chunk_id, timestamp_sec, frame_path)
                            VALUES ($1, $2, $3)
                            """,
                            uuid.UUID(frame_embed_chunk),
                            frame["timestamp"],
                            None,
                        )
                        await store_embedding(
                            tenant_id=tenant_id,
                            chunk_id=frame_embed_chunk,
                            embedding=frame["embedding"],
                            payload={"modality": "video_frame", "document_id": document_id, "timestamp": frame["timestamp"]},
                        )

                await conn.execute(
                    "UPDATE documents SET status = 'completed', updated_at = now() WHERE id = $1",
                    uuid.UUID(document_id),
                )
                await publish_event("EMBED", f"Stored embeddings to Qdrant for {filename}", "success", document_id=document_id, tenant_id=tenant_id)
                await publish_event("VECTOR", f"Document indexed in collection tenant_{tenant_id}", "success", document_id=document_id, tenant_id=tenant_id)
                await publish_event("METADATA", f"Document {document_id[:8]}... status updated to completed", "success", document_id=document_id, tenant_id=tenant_id)
                logger.info("Multimodal job %s completed for document %s", job_id, document_id)
            except Exception as e:
                logger.exception("Multimodal job %s failed: %s", job_id, e)
                await publish_event("INTAKE", f"Multimodal job failed for {filename}: {str(e)[:100]}", "error", document_id=document_id, tenant_id=tenant_id)
                await conn.execute(
                    "UPDATE documents SET status = 'failed', updated_at = now() WHERE id = $1",
                    uuid.UUID(document_id),
                )
            finally:
                await conn.close()

        except Exception as e:
            logger.exception("Worker error: %s", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_worker())
