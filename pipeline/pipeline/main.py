"""
Frostbyte ETL Pipeline — 1hr MVP.
Intake -> parse (stub) -> store metadata + vectors.
Single-tenant, local Docker. Per docs/PRD.md and docs/TECH_DECISIONS.md.
"""
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import boto3
import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from . import db
from .config import PlatformConfig
from .intake.routes import router as intake_router

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
app.include_router(intake_router)


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


@app.post("/api/v1/intake", response_model=IntakeResponse)
async def intake(
    file: UploadFile = File(...),
    tenant_id: str = Form(default=TENANT_DEFAULT),
):
    """Ingest a document: store in MinIO, parse stub, store metadata + vector stub."""
    doc_id = str(uuid.uuid4())
    key = f"{tenant_id}/{doc_id}/{file.filename or 'document'}"

    contents = await file.read()
    s3 = get_s3()
    s3.put_object(Bucket=BUCKET, Key=key, Body=contents)

    # Parse stub: treat as plain text
    text = contents.decode("utf-8", errors="replace")[:10_000]

    # Embed stub: 768 zero vector (per TECH_DECISIONS 768d lock)
    vector = [0.0] * 768

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

    # Store metadata (in-memory for 1hr; replace with PostgreSQL)
    _docs[doc_id] = {
        "id": doc_id,
        "tenant_id": tenant_id,
        "bucket": BUCKET,
        "object_key": key,
        "status": "ingested",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    return IntakeResponse(
        document_id=doc_id,
        status="ingested",
        bucket=BUCKET,
        object_key=key,
        created_at=_docs[doc_id]["created_at"],
    )


@app.get("/api/v1/documents/{document_id}")
async def get_document(document_id: str):
    if document_id not in _docs:
        raise HTTPException(status_code=404, detail="Document not found")
    return _docs[document_id]
