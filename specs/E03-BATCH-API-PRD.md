# Enhancement #3 – Batch Processing API with Progress Streaming

## All-In-One Zero-Shot PRD

**Status:** Deterministic, executable  
**Format:** COSTAR System Prompt + Zero-Shot Prompt + PRD + Implementation Plan

---

## COSTAR System Prompt

```
[CONTEXT]
You are implementing a batch processing API for the Frostbyte ETL pipeline. The API must accept bulk document upload jobs and stream progress updates via Server‑Sent Events (SSE). The PRD defines exactly the endpoints, request/response schemas, and the internal job queue mechanism.

[OBJECTIVE]
Generate the FastAPI endpoint handlers, Pydantic models, and the background worker logic as specified. Use Redis as the job broker. All code must be production‑ready and include error handling.

[STYLE]
Imperative, copy‑pasta ready. Provide each file in a code block with its full relative path. No commentary.

[AUDIENCE]
Backend developer. Execute the steps exactly as written.
```

---

## Production Requirements Document (PRD) – Batch API with Progress Streaming

### 1. New API Endpoints

| Method | Path                          | Description                          |
|--------|-------------------------------|--------------------------------------|
| POST   | `/batch/jobs`                 | Submit a batch job (multiple documents). |
| GET    | `/batch/jobs/{job_id}`        | Get job metadata and summary status. |
| GET    | `/batch/jobs/{job_id}/stream` | SSE stream of job progress events.  |
| DELETE | `/batch/jobs/{job_id}`        | Cancel a running job.                |

### 2. Job Request Schema (`BatchJobCreate`)

```json
{
  "tenant_id": "uuid",
  "documents": [
    {
      "filename": "string",
      "content": "base64 encoded",
      "metadata": {}
    }
  ],
  "collection": "string (optional)",
  "priority": "integer (1-10, default 5)"
}
```

### 3. Job Response Schema (`BatchJob`)

```json
{
  "job_id": "uuid",
  "tenant_id": "uuid",
  "status": "pending | processing | completed | failed | cancelled",
  "total_documents": "integer",
  "processed_count": "integer",
  "failed_count": "integer",
  "created_at": "datetime",
  "updated_at": "datetime",
  "collection": "string",
  "priority": "integer"
}
```

### 4. Progress Events (SSE)

Each event is a JSON object with fields:

```json
{
  "job_id": "uuid",
  "event_type": "start | progress | complete | fail | cancel",
  "document_index": "integer (for progress)",
  "filename": "string (for progress)",
  "message": "string",
  "timestamp": "datetime"
}
```

### 5. Job Queue Implementation

- **Broker**: Redis (localhost:6379, database 0).
- **Queue name**: `batch:jobs` (list).
- **Worker**: Single background task started with FastAPI startup event.
- **Processing**: Pop from list, process documents sequentially, publish SSE events to Redis pub/sub channel `job:events:{job_id}`.

### 6. SSE Streaming

- Endpoint `/batch/jobs/{job_id}/stream` subscribes to the Redis pub/sub channel and yields SSE events.
- Connection **must** close when job status is `completed`, `failed`, or `cancelled`.
- Use `sse-starlette` library for SSE.

---

## Deterministic Implementation Plan

**Project paths:** All `app/` paths map to `pipeline/pipeline/` in the Frostbyte repo.

### Step 1 – Install dependencies

```bash
cd pipeline
pip install redis sse-starlette
```

Add to `pyproject.toml`:

```toml
dependencies = [
  ...
  "redis>=5.0",
  "sse-starlette>=2.0",
]
```

### Step 2 – Add Redis configuration to `.env.example`

```
REDIS_URL=redis://localhost:6379/0
```

### Step 3 – Create Pydantic models

**File: `pipeline/pipeline/schemas/batch.py`**

```python
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BatchDocument(BaseModel):
    filename: str
    content: str  # base64 encoded
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchJobCreate(BaseModel):
    tenant_id: UUID
    documents: List[BatchDocument]
    collection: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)


class BatchJob(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    status: str = "pending"
    total_documents: int
    processed_count: int = 0
    failed_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    collection: Optional[str] = None
    priority: int = 5


class ProgressEvent(BaseModel):
    job_id: UUID
    event_type: str  # start, progress, complete, fail, cancel
    document_index: Optional[int] = None
    filename: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### Step 4 – Create database migration for `batch_jobs` table

**File: `migrations/007_batch_jobs.sql`**

```sql
-- batch_jobs: batch document processing jobs with progress tracking
CREATE TABLE IF NOT EXISTS batch_jobs (
    job_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_documents INTEGER NOT NULL,
    processed_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    collection VARCHAR(255),
    priority INTEGER NOT NULL DEFAULT 5
);

CREATE INDEX idx_batch_jobs_tenant ON batch_jobs(tenant_id);
CREATE INDEX idx_batch_jobs_status ON batch_jobs(status);
```

### Step 5 – Create FastAPI batch routes

**File: `pipeline/pipeline/routes/batch.py`**

```python
import json
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ..schemas.batch import BatchJob, BatchJobCreate

router = APIRouter(prefix="/batch", tags=["batch"])
REDIS_URL = "redis://localhost:6379/0"


async def _get_redis():
    return redis.from_url(REDIS_URL)


@router.post("/jobs", response_model=BatchJob)
async def create_batch_job(payload: BatchJobCreate):
    from .. import db
    pool = db._get_pool()
    async with pool.acquire() as conn:
        tenant = await conn.fetchval(
            "SELECT 1 FROM tenants WHERE tenant_id = $1", payload.tenant_id
        )
        if not tenant:
            raise HTTPException(404, "Tenant not found")

        job = BatchJob(
            tenant_id=payload.tenant_id,
            total_documents=len(payload.documents),
            collection=payload.collection,
            priority=payload.priority,
        )

        await conn.execute(
            """
            INSERT INTO batch_jobs (job_id, tenant_id, status, total_documents, collection, priority, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            job.job_id,
            job.tenant_id,
            job.status,
            job.total_documents,
            payload.collection,
            job.priority,
            job.created_at,
            job.updated_at,
        )

    r = await _get_redis()
    await r.rpush(
        "batch:jobs",
        json.dumps({
            "job_id": str(job.job_id),
            "documents": [d.model_dump() for d in payload.documents],
            "collection": payload.collection,
            "tenant_id": str(payload.tenant_id),
        }),
    )
    await r.close()

    return job


@router.get("/jobs/{job_id}", response_model=BatchJob)
async def get_batch_job(job_id: UUID):
    from .. import db
    pool = db._get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM batch_jobs WHERE job_id = $1", job_id)
    if not row:
        raise HTTPException(404, "Job not found")
    return dict(row)


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: UUID, request: Request):
    from .. import db
    pool = db._get_pool()
    async with pool.acquire() as conn:
        status = await conn.fetchval(
            "SELECT status FROM batch_jobs WHERE job_id = $1", job_id
        )
    if not status:
        raise HTTPException(404, "Job not found")

    r = await _get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"job:events:{job_id}")

    async def event_generator():
        try:
            while not await request.is_disconnected():
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message.get("data"):
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield {"event": "progress", "data": data}
                from .. import db as db_mod
                pool = db_mod._get_pool()
                async with pool.acquire() as conn:
                    s = await conn.fetchval(
                        "SELECT status FROM batch_jobs WHERE job_id = $1", job_id
                    )
                if s in ("completed", "failed", "cancelled"):
                    yield {
                        "event": "complete",
                        "data": json.dumps({"status": s}),
                    }
                    break
        finally:
            await pubsub.unsubscribe(f"job:events:{job_id}")
            await pubsub.close()
            await r.close()

    return EventSourceResponse(event_generator())


@router.delete("/jobs/{job_id}")
async def cancel_batch_job(job_id: UUID):
    from .. import db
    pool = db._get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE batch_jobs SET status = 'cancelled', updated_at = now()
            WHERE job_id = $1 AND status IN ('pending', 'processing')
            """,
            job_id,
        )
    if "UPDATE 0" in str(result):
        raise HTTPException(404, "Job not found or not cancellable")

    r = await _get_redis()
    await r.publish(
        f"job:events:{job_id}",
        json.dumps({"event_type": "cancel", "message": "Job cancelled by user"}),
    )
    await r.close()
    return {"status": "cancelled"}
```

### Step 6 – Create background worker

**File: `pipeline/pipeline/worker/batch_worker.py`**

**Integration:** The worker must call the same path as the intake gateway: write file to MinIO `raw/{tenant_id}/{file_id}/{sha256}`, enqueue to Redis `tenant:{tenant_id}:queue:parse`, emit audit events. Use existing `storage`, `parse_enqueue`, and `emit_audit_event` modules.

```python
import asyncio
import base64
import hashlib
import json
import uuid
from datetime import datetime
from uuid import UUID

import redis.asyncio as redis

from .. import db
from ..parse_enqueue import enqueue_parse

REDIS_URL = "redis://localhost:6379/0"


async def process_document(tenant_id: UUID, doc: dict, batch_id: str) -> bool:
    """Process a single document. Writes to MinIO, enqueues parse, emits audit. Returns True on success."""
    filename = doc.get("filename", "unknown")
    content_b64 = doc.get("content", "")
    metadata = doc.get("metadata", {})
    try:
        content = base64.b64decode(content_b64)
    except Exception:
        return False
    file_id = str(uuid.uuid4())
    sha256 = hashlib.sha256(content).hexdigest()
    storage_path = f"raw/{tenant_id}/{file_id}/{sha256}"
    # REQUIRED: Write content to MinIO bucket at key storage_path (use boto3 S3 client / main.get_s3())
    # Then enqueue so parse worker can BRPOP and fetch the file
    await enqueue_parse(
        file_id=file_id, batch_id=batch_id, sha256=sha256,
        storage_path=storage_path, tenant_id=str(tenant_id),
    )
    await db.emit_audit_event(
        event_id=uuid.uuid4(), tenant_id=str(tenant_id), event_type="DOCUMENT_INGESTED",
        resource_type="document", resource_id=file_id, details={"filename": filename},
    )
    return True


async def batch_worker():
    r = redis.from_url(REDIS_URL)
    pool = db._get_pool()

    while True:
        try:
            _, payload = await r.blpop("batch:jobs", timeout=1)
            if not payload:
                continue

            data = json.loads(payload)
            job_id = data["job_id"]
            documents = data["documents"]
            tenant_id = UUID(data["tenant_id"])
            collection = data.get("collection")

            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE batch_jobs SET status = 'processing', updated_at = now() WHERE job_id = $1",
                    job_id,
                )

            await r.publish(
                f"job:events:{job_id}",
                json.dumps({"event_type": "start", "message": "Job started"}),
            )

            processed = 0
            failed = 0
            async with pool.acquire() as conn:
                for idx, doc in enumerate(documents):
                    try:
                        ok = await process_document(tenant_id, doc, job_id)
                        if ok:
                            processed += 1
                            await r.publish(
                                f"job:events:{job_id}",
                                json.dumps({
                                    "event_type": "progress",
                                    "document_index": idx,
                                    "filename": doc.get("filename"),
                                    "message": "Processed",
                                    "timestamp": datetime.utcnow().isoformat(),
                                }),
                            )
                        else:
                            failed += 1
                            await r.publish(
                                f"job:events:{job_id}",
                                json.dumps({
                                    "event_type": "fail",
                                    "document_index": idx,
                                    "filename": doc.get("filename"),
                                    "message": "Decode or ingest failed",
                                    "timestamp": datetime.utcnow().isoformat(),
                                }),
                            )
                    except Exception as e:
                        failed += 1
                        await r.publish(
                            f"job:events:{job_id}",
                            json.dumps({
                                "event_type": "fail",
                                "document_index": idx,
                                "filename": doc.get("filename"),
                                "message": str(e),
                                "timestamp": datetime.utcnow().isoformat(),
                            }),
                        )

            final_status = "completed" if failed == 0 else "failed"
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE batch_jobs
                    SET status = $1, processed_count = $2, failed_count = $3, updated_at = now()
                    WHERE job_id = $4
                    """,
                    final_status,
                    processed,
                    failed,
                    job_id,
                )

            await r.publish(
                f"job:events:{job_id}",
                json.dumps({"event_type": "complete", "message": final_status}),
            )

        except Exception as e:
            print(f"Batch worker error: {e}")
            await asyncio.sleep(5)

    await r.close()
```

**Integration note:** Replace `ingest_single_file` with the actual Frostbyte intake/parse flow (e.g., MinIO upload + Redis enqueue to `tenant:{tenant_id}:queue:parse`).

### Step 7 – Register routes and startup event in `pipeline/main.py`

```python
from pipeline.routes.batch import router as batch_router
from pipeline.worker.batch_worker import batch_worker

app.include_router(batch_router, prefix="/api/v1")

@app.on_event("startup")
async def start_batch_worker():
    asyncio.create_task(batch_worker())
```

### Step 8 – Run migration

```bash
./scripts/run_migrations.sh
```

### Step 9 – Commit

```bash
git add pipeline/pipeline/schemas/batch.py pipeline/pipeline/routes/batch.py pipeline/pipeline/worker/
git add migrations/007_batch_jobs.sql
git commit -m "feat(batch): add batch processing API with SSE progress streaming"
```
