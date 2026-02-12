#!/usr/bin/env python3
"""
Parse worker: BRPOP from tenant parse queues, parse documents, write canonical JSON, enqueue policy.
Per PARSING_PIPELINE_PLAN. Run: python scripts/run_parse_worker.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
import uuid
from pathlib import Path

# Add pipeline to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parse_worker")

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
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS,
        aws_secret_access_key=MINIO_SECRET,
        region_name="us-east-1",
    )


async def _load_tenant_ids():
    """Load ACTIVE tenant IDs from control-plane DB."""
    try:
        from pipeline import db
        from pipeline.config import PlatformConfig
        cfg = PlatformConfig.from_env()
        await db.init_db(cfg.control_db_url)
        pool = db._get_pool()
        rows = await pool.fetch("SELECT tenant_id FROM tenants WHERE state = 'ACTIVE'")
        return [r["tenant_id"] for r in rows]
    except Exception as e:
        logger.warning("Could not load tenants from DB: %s. Using default tenant.", e)
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


def _process_job(payload: dict):
    """Process a single parse job. Sync to avoid event-loop issues with Unstructured."""
    from pipeline.parsing.stages import parse_file, ParseError
    from pipeline.policy_enqueue import enqueue_policy

    file_id = payload["file_id"]
    batch_id = payload["batch_id"]
    sha256 = payload["sha256"]
    storage_path = payload["storage_path"]
    tenant_id = payload["tenant_id"]
    mime_type = payload.get("mime_type")

    s3 = _get_s3()

    # Idempotency: doc_id is deterministic from file_id
    doc_id_predicted = f"doc_{__import__('hashlib').sha256(file_id.encode()).hexdigest()[:12]}"
    normalized_path = f"normalized/{tenant_id}/{doc_id_predicted}/structured.json"
    try:
        obj = s3.head_object(Bucket=BUCKET, Key=normalized_path)
        # Could add lineage check via get_object + parse; for now skip if exists
        logger.info("Skip (exists): %s", normalized_path)
        return None  # Signal skip, no audit
    except Exception:
        pass

    with tempfile.NamedTemporaryFile(suffix=Path(storage_path).name or ".bin", delete=False) as f:
        try:
            s3.download_fileobj(BUCKET, storage_path, f)
            local_path = f.name
        except Exception as e:
            raise RuntimeError(f"Download failed: {e}") from e

    try:
        doc = parse_file(
            input_path=local_path,
            file_id=file_id,
            tenant_id=tenant_id,
            sha256=sha256,
            mime_type=mime_type,
        )
    except ParseError:
        raise
    except Exception as e:
        raise RuntimeError(str(e)) from e
    finally:
        try:
            os.unlink(local_path)
        except OSError:
            pass

    # Write canonical JSON to MinIO
    normalized_path = f"normalized/{tenant_id}/{doc.doc_id}/structured.json"
    body = doc.model_dump_json(indent=2).encode("utf-8")
    s3.put_object(Bucket=BUCKET, Key=normalized_path, Body=body)

    # Enqueue policy job
    enqueue_policy(
        doc_id=doc.doc_id,
        file_id=file_id,
        tenant_id=tenant_id,
        storage_path=normalized_path,
    )

    return doc


async def _run_job(payload: dict) -> bool:
    """Run job in executor (Unstructured may block). Returns True if success."""
    loop = asyncio.get_event_loop()
    try:
        doc = await loop.run_in_executor(None, _process_job, payload)
        if doc is None:
            return True  # Skipped (idempotent)
        await _emit_audit(
            tenant_id=payload["tenant_id"],
            event_type="DOCUMENT_PARSED",
            resource_id=doc.doc_id,
            details={
                "chunk_count": doc.stats.chunk_count,
                "page_count": doc.stats.page_count,
                "parser_versions": [
                    doc.lineage.stage1_parser_version,
                    doc.lineage.stage2_parser_version,
                ],
                "component": "parse-worker",
            },
        )
        logger.info("Parsed %s -> %s", payload["file_id"], doc.doc_id)
        return True
    except Exception as e:
        reason = getattr(e, "reason", "PARSER_ERROR")
        msg = str(e)
        await _emit_audit(
            tenant_id=payload["tenant_id"],
            event_type="DOCUMENT_PARSE_FAILED",
            resource_id=payload["file_id"],
            details={
                "failure_reason": reason,
                "message": msg,
                "component": "parse-worker",
            },
        )
        logger.error("Parse failed %s: %s", payload["file_id"], msg)
        return False


async def main():
    redis_client = _get_redis()
    last_tenant_refresh = 0.0
    tenant_ids = ["default"]

    while True:
        # Refresh tenant list periodically
        import time
        now = time.monotonic()
        if now - last_tenant_refresh > TENANT_REFRESH_INTERVAL:
            tenant_ids = await _load_tenant_ids()
            last_tenant_refresh = now

        keys = [f"tenant:{t}:queue:parse" for t in tenant_ids]
        if not keys:
            await asyncio.sleep(5)
            continue

        # BRPOP blocks; run in executor
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

        await _run_job(payload)


if __name__ == "__main__":
    asyncio.run(main())
