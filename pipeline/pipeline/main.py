"""
Frostbyte ETL Pipeline — 1hr MVP.
Intake -> parse (stub) -> store metadata + vectors.
Single-tenant, local Docker. Per docs/product/PRD.md and docs/reference/TECH_DECISIONS.md.
Multi-modal support: images, audio, video (Enhancement #9).
"""
import base64
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import boto3
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from . import db
from .config import PlatformConfig
from .events import publish_async, publish_unimplemented_stages
from .intake.routes import router as intake_router
from .multimodal import detect_modality
from .routes.auth_routes import router as auth_router
from .routes.collections import router as collections_router
from .routes.pipeline import router as pipeline_router
from .routes.tenant_schemas import router as tenant_schemas_router

# Config from env
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET = os.getenv("MINIO_SECRET_KEY", "minioadmin")
POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql+asyncpg://frostbyte:frostbyte@localhost:5432/frostbyte"
)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
BUCKET = os.getenv("BUCKET", "frostbyte-docs")
TENANT_DEFAULT = "default"

# Clients (lazy init)
_s3 = None
_qdrant = None
_pg_pool = None


def get_s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS,
            aws_secret_access_key=MINIO_SECRET,
            region_name="us-east-1",
        )
        try:
            _s3.create_bucket(Bucket=BUCKET)
        except Exception:
            pass  # bucket exists
    return _s3


def get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL)
        coll = f"tenant_{TENANT_DEFAULT}"
        try:
            _qdrant.get_collection(coll)
        except Exception:
            _qdrant.create_collection(
                collection_name=coll,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
    return _qdrant


# In-memory doc store for 1hr MVP (replace with PostgreSQL + SQLAlchemy)
_docs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_s3()
    get_qdrant()
    # Init control-plane DB if configured (foundation layer)
    try:
        cfg = PlatformConfig.from_env()
        await db.init_db(cfg.control_db_url)
    except Exception as e:
        logging.getLogger("uvicorn.error").warning("Control-plane DB init skipped: %s", e)
    yield
    try:
        await db.close_db()
    except Exception:
        pass


app = FastAPI(title="Frostbyte ETL", version="0.1.0", lifespan=lifespan)

# CORS — allow admin dashboard (dev: localhost:5174, prod: configure via env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5174").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(intake_router)
app.include_router(collections_router)
app.include_router(pipeline_router)
app.include_router(tenant_schemas_router)


def _check_service(name: str, url: str) -> bool:
    try:
        r = httpx.get(url, timeout=2.0)
        return r.status_code in (200, 204)
    except Exception:
        return False


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Visual pipeline status — linear flow diagram + service health."""
    minio_ok = _check_service("MinIO", f"{MINIO_ENDPOINT}/minio/health/live")
    qdrant_ok = _check_service("Qdrant", f"{QDRANT_URL}/readyz")
    doc_count = len(_docs)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Frostbyte Pipeline — Status</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
    h1 {{ font-size: 1.5rem; }}
    .flow {{ background: #f5f5f5; padding: 1rem; margin: 1rem 0; border-radius: 4px; }}
    .flow ol {{ margin: 0; padding-left: 1.5rem; }}
    .flow li {{ margin: 0.5rem 0; }}
    .status {{ display: flex; gap: 1rem; margin: 1rem 0; flex-wrap: wrap; }}
    .status span {{ padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 500; }}
    .ok {{ background: #d4edda; color: #155724; }}
    .fail {{ background: #f8d7da; color: #721c24; }}
    .docs {{ margin-top: 1rem; font-size: 0.9rem; color: #666; }}
  </style>
</head>
<body>
  <h1>Frostbyte ETL Pipeline — Status</h1>

  <h2>Data flow (left to right)</h2>
  <div class="flow">
    <ol>
      <li><strong>You upload a file</strong> → POST to <code>/api/v1/intake</code></li>
      <li><strong>Pipeline API</strong> receives it (this server)</li>
      <li><strong>MinIO</strong> stores the raw file (object store, port 9000)</li>
      <li><strong>Qdrant</strong> stores the vector (768d, port 6333)</li>
    </ol>
  </div>

  <h2>Service status</h2>
  <div class="status">
    <span class="{'ok' if minio_ok else 'fail'}">MinIO {'OK' if minio_ok else 'DOWN'}</span>
    <span class="{'ok' if qdrant_ok else 'fail'}">Qdrant {'OK' if qdrant_ok else 'DOWN'}</span>
    <span class="ok">Pipeline API OK</span>
  </div>

  <div class="docs">Documents ingested this session: <strong>{doc_count}</strong></div>

  <p style="margin-top: 2rem;">
    <a href="/docs">API documentation (Swagger)</a> &middot;
    <a href="/health">Health check (JSON)</a>
  </p>
</body>
</html>"""
    return html


class IntakeResponse(BaseModel):
    document_id: str
    status: str
    bucket: str
    object_key: str
    created_at: str


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}


REDIS_URL = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))


@app.get("/api/v1/pipeline/stream")
async def pipeline_stream(request: Request):
    """SSE endpoint: streams real-time pipeline events from Redis pub/sub."""

    async def _event_generator():
        # Welcome message with stage status
        welcome = json.dumps({
            "stage": "SYSTEM",
            "message": "Pipeline log stream connected. Live stages: INTAKE, PARSE. Other stages pending implementation.",
            "level": "info",
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        })
        yield {"data": welcome}

        # Subscribe to pipeline events channel
        sub = redis.from_url(REDIS_URL)
        ps = sub.pubsub()
        await ps.subscribe("pipeline:events")
        try:
            while True:
                if await request.is_disconnected():
                    break
                msg = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg["type"] == "message":
                    yield {"data": msg["data"].decode() if isinstance(msg["data"], bytes) else msg["data"]}
        finally:
            await ps.unsubscribe("pipeline:events")
            await ps.aclose()
            await sub.aclose()

    return EventSourceResponse(_event_generator())


@app.post("/api/v1/intake", response_model=IntakeResponse)
async def intake(
    file: UploadFile = File(...),
    tenant_id: str = Form(default=TENANT_DEFAULT),
):
    """Ingest a document: store in MinIO. Multimodal (image/audio/video) -> background worker."""
    filename = file.filename or "document"
    contents = await file.read()
    modality = detect_modality(filename)
    await publish_async("INTAKE", f"File received: {filename} ({modality}, {len(contents)} bytes)", "info", tenant_id=tenant_id)

    # Multimodal: push to worker, return processing status
    if modality in ("image", "audio", "video"):
        try:
            doc_id = await db.insert_document(
                tenant_id=tenant_id,
                filename=filename,
                status="processing",
                modality=modality,
            )
            key = f"{tenant_id}/{doc_id}/{filename}"
            s3 = get_s3()
            s3.put_object(Bucket=BUCKET, Key=key, Body=contents)
            await publish_async("INTAKE", f"Stored to MinIO: {key}", "success", document_id=str(doc_id), tenant_id=tenant_id)
            r = redis.from_url(REDIS_URL)
            await r.rpush(
                "multimodal:jobs",
                json.dumps({
                    "job_id": str(uuid.uuid4()),
                    "document_id": str(doc_id),
                    "tenant_id": tenant_id,
                    "filename": filename,
                    "content": base64.b64encode(contents).decode("ascii"),
                }),
            )
            await r.aclose()
            await publish_async("INTAKE", f"Multimodal job queued: {modality} worker will process {filename}", "info", document_id=str(doc_id), tenant_id=tenant_id)
            now = datetime.utcnow().isoformat() + "Z"
            _docs[str(doc_id)] = {
                "id": str(doc_id),
                "tenant_id": tenant_id,
                "bucket": BUCKET,
                "object_key": key,
                "status": "processing",
                "created_at": now,
            }
            return IntakeResponse(
                document_id=str(doc_id),
                status="processing",
                bucket=BUCKET,
                object_key=key,
                created_at=now,
            )
        except Exception as e:
            await publish_async("INTAKE", f"Error: {e}", "error", tenant_id=tenant_id)
            if "does not exist" in str(e).lower() or "relation" in str(e).lower():
                raise HTTPException(status_code=503, detail="Documents table not ready; run migration 007")
            raise

    # Text path: existing flow
    doc_id = str(uuid.uuid4())
    key = f"{tenant_id}/{doc_id}/{filename}"
    s3 = get_s3()
    s3.put_object(Bucket=BUCKET, Key=key, Body=contents)
    await publish_async("INTAKE", f"Stored to MinIO: {key}", "success", document_id=doc_id, tenant_id=tenant_id)

    # Parse stub: treat as plain text
    text = contents.decode("utf-8", errors="replace")[:10_000]
    await publish_async("PARSE", f"Inline parse: extracted {len(text)} chars from {filename}", "info", document_id=doc_id, tenant_id=tenant_id)

    # Embed stub: 768 zero vector (per TECH_DECISIONS 768d lock)
    vector = [0.0] * 768
    await publish_async("EMBED", f"Generated 768d stub embedding for {filename}", "info", document_id=doc_id, tenant_id=tenant_id)

    # Store vector in Qdrant
    qdrant = get_qdrant()
    coll = f"tenant_{tenant_id}"
    try:
        qdrant.get_collection(coll)
    except Exception:
        qdrant.create_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
    qdrant.upsert(
        collection_name=coll,
        points=[
            PointStruct(
                id=hash(doc_id) % (2**63),
                vector=vector,
                payload={"doc_id": doc_id, "tenant_id": tenant_id, "preview": text[:200]},
            )
        ],
    )
    await publish_async("VECTOR", f"Upserted to Qdrant collection {coll}", "success", document_id=doc_id, tenant_id=tenant_id)

    # Store metadata (in-memory for 1hr; replace with PostgreSQL)
    _docs[doc_id] = {
        "id": doc_id,
        "tenant_id": tenant_id,
        "bucket": BUCKET,
        "object_key": key,
        "status": "ingested",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    await publish_async("METADATA", f"Document {doc_id[:8]}... indexed in memory store", "success", document_id=doc_id, tenant_id=tenant_id)

    # Emit status for unimplemented stages
    await publish_unimplemented_stages()

    return IntakeResponse(
        document_id=doc_id,
        status="ingested",
        bucket=BUCKET,
        object_key=key,
        created_at=_docs[doc_id]["created_at"],
    )


@app.get("/api/v1/documents/{document_id}")
async def get_document(document_id: str):
    if document_id in _docs:
        return _docs[document_id]
    try:
        doc = await db.fetch_document(uuid.UUID(document_id))
        if doc:
            return doc
    except ValueError:
        pass
    raise HTTPException(status_code=404, detail="Document not found")
