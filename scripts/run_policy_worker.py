#!/usr/bin/env python3
"""
Policy worker: consumes policy jobs from Redis, runs governance gates, enqueues embedding jobs.

ARCHITECTURE (enterprise pipeline pattern)
------------------------------------------
A "worker" is a long-running process that does one stage of the pipeline. It does not serve HTTP;
it only listens to a queue (here, Redis lists). This decouples stages: the parse worker writes
jobs to tenant:{id}:queue:policy, and this worker consumes them. Downstream, the embedding worker
consumes tenant:{id}:queue:embedding. Queues allow horizontal scaling (run N policy workers) and
retry/dead-letter patterns.

Flow: Parse Worker → [Redis tenant:{id}:queue:policy] → Policy Worker (this script)
                         → [Redis tenant:{id}:queue:embedding] → Embedding Worker

Per POLICY_ENGINE_PLAN: Gate 1 (PII) → Gate 2 (Classification) → Gate 3 (Injection).
Only chunks that pass (or are FLAGged) are sent to embedding; BLOCK/QUARANTINE chunks are dropped.

Run: python scripts/run_policy_worker.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path

# Project root so we can import pipeline
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("policy_worker")

import boto3

from pipeline.events import publish as publish_event
from pipeline.policy.service import run_policy_gates
from pipeline.embedding_enqueue import enqueue_embedding
from pipeline.parsing.models import CanonicalStructuredDocument

BUCKET = os.getenv("BUCKET", "frostbyte-docs")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET = os.getenv("MINIO_SECRET_KEY", "minioadmin")
REDIS_URL = os.getenv("FROSTBYTE_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
BRPOP_TIMEOUT = 5
TENANT_REFRESH_INTERVAL = 60


def _get_redis():
    import redis
    return redis.from_url(REDIS_URL)


def _get_s3():
    """S3/MinIO client for reading canonical structured JSON written by the parse worker."""
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS,
        aws_secret_access_key=MINIO_SECRET,
        region_name="us-east-1",
    )


async def _load_tenant_ids():
    """Load ACTIVE tenant IDs from control-plane DB so we know which queues to listen to."""
    try:
        from pipeline import db
        from pipeline.config import PlatformConfig
        cfg = PlatformConfig.from_env()
        await db.init_db(cfg.control_db_url)
        pool = db._get_pool()
        rows = await pool.fetch("SELECT tenant_id FROM tenants WHERE state = 'ACTIVE'")
        return [r["tenant_id"] for r in rows]
    except Exception as e:
        logger.warning("Could not load tenants from DB: %s. Using default.", e)
        return ["default"]


async def _emit_audit(tenant_id: str, event_type: str, resource_id: str, details: dict) -> None:
    try:
        from pipeline import db
        await db.emit_audit_event(
            event_id=uuid.uuid4(),
            tenant_id=tenant_id,
            event_type=event_type,
            resource_type="document",
            resource_id=resource_id,
            details=details,
        )
    except Exception as e:
        logger.warning("Audit emit failed: %s", e)


def _process_job(payload: dict) -> bool:
    """
    Process one policy job (sync so we can run in executor if needed).
    Downloads structured JSON from MinIO, runs gates, enqueues embedding for passing chunks.
    Returns True on success, False on failure.
    """
    doc_id = payload["doc_id"]
    file_id = payload["file_id"]
    tenant_id = payload["tenant_id"]
    storage_path = payload["storage_path"]

    s3 = _get_s3()
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=storage_path)
        body = obj["Body"].read().decode("utf-8")
    except Exception as e:
        logger.error("Failed to download %s: %s", storage_path, e)
        publish_event("EVIDENCE", f"Policy job failed: cannot read {storage_path}", "error", document_id=doc_id, tenant_id=tenant_id)
        return False

    try:
        doc = CanonicalStructuredDocument.model_validate_json(body)
    except Exception as e:
        logger.error("Invalid structured JSON for %s: %s", storage_path, e)
        publish_event("EVIDENCE", f"Policy job failed: invalid JSON", "error", document_id=doc_id, tenant_id=tenant_id)
        return False

    # Tenant config: in production load from DB; here use defaults (no PII block, no injection quarantine)
    tenant_config = {}

    publish_event("EVIDENCE", f"Running policy gates (PII → Classification → Injection) for {doc_id}", "info", document_id=doc_id, tenant_id=tenant_id)
    passing_chunks, quarantined_count, document_blocked = run_policy_gates(
        doc, tenant_config, original_filename=file_id
    )

    if document_blocked:
        logger.warning("Document %s blocked by policy (e.g. PII BLOCK)", doc_id)
        publish_event("EVIDENCE", f"Document blocked by policy; not sent to embedding", "warn", document_id=doc_id, tenant_id=tenant_id)
        return True  # Job handled

    if not passing_chunks:
        logger.warning("No passing chunks for %s (all quarantined: %s)", doc_id, quarantined_count)
        publish_event("EVIDENCE", f"No chunks passed gates (quarantined: {quarantined_count})", "warn", document_id=doc_id, tenant_id=tenant_id)
        return True

    # Serialize passing chunks for the embedding worker (embedding worker expects list of dicts)
    chunks_payload = [c.model_dump() for c in passing_chunks]

    enqueue_embedding(
        doc_id=doc_id,
        file_id=file_id,
        tenant_id=tenant_id,
        storage_path=storage_path,
        chunks=chunks_payload,
    )
    publish_event("EVIDENCE", f"Policy passed: {len(passing_chunks)} chunks enqueued for embedding (quarantined: {quarantined_count})", "success", document_id=doc_id, tenant_id=tenant_id)
    logger.info("Policy done for %s: %d chunks → embedding queue", doc_id, len(passing_chunks))
    return True


async def main():
    """Main loop: refresh tenant list periodically, BRPOP policy queues, process jobs."""
    import time
    redis_client = _get_redis()
    last_tenant_refresh = 0.0
    tenant_ids = ["default"]

    while True:
        now = time.monotonic()
        if now - last_tenant_refresh > TENANT_REFRESH_INTERVAL:
            tenant_ids = await _load_tenant_ids()
            last_tenant_refresh = now

        keys = [f"tenant:{t}:queue:policy" for t in tenant_ids]
        if not keys:
            await asyncio.sleep(5)
            continue

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: redis_client.brpop(keys, timeout=BRPOP_TIMEOUT),
        )

        if result is None:
            continue

        key, value = result
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as e:
            logger.error("Invalid job JSON: %s", e)
            continue

        await loop.run_in_executor(None, _process_job, payload)


if __name__ == "__main__":
    asyncio.run(main())
