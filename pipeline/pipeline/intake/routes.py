"""
Intake gateway API routes per INTAKE_GATEWAY_PLAN Section 3.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from .. import auth, ratelimit
from ..clamav_client import scan_bytes
from ..parse_enqueue import enqueue_parse
from ..events import publish_async
from . import receipt_store
from . import service
from .models import (
    BatchManifest,
    BatchReceiptResponse,
)

router = APIRouter(prefix="/api/v1/ingest", tags=["intake"])

# In-memory batch status (batch metadata; receipts in PostgreSQL)
_batches: dict[str, dict] = {}


async def _emit_audit(tenant_id: str, event_type: str, resource_id: str, details: dict) -> None:
    """Emit audit event via foundation layer."""
    try:
        from .. import db
        await db.emit_audit_event(
            event_id=uuid.uuid4(),
            tenant_id=tenant_id,
            event_type=event_type,
            resource_type="document" if "DOCUMENT" in event_type else "batch",
            resource_id=resource_id,
            details=details,
        )
    except Exception:
        pass


async def _get_tenant_config(tenant_id: str) -> dict:
    """Load tenant config. Fallback to defaults if DB unavailable."""
    try:
        from .. import db
        return await db.load_tenant_config(tenant_id)
    except Exception:
        return {"config": {}, "config_version": 1}


async def _malware_scan(content: bytes) -> tuple[str, str | None]:
    """ClamAV instream scan. Returns (scan_result, threat_name)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, scan_bytes, content)


@router.post("/{tenant_id}/batch")
async def post_batch(
    tenant_id: str,
    manifest: str = Form(..., alias="manifest"),
    files: list[UploadFile] = File(..., alias="files"),
    token_tenant_id: Annotated[str | None, Depends(auth.get_tenant_from_token)] = None,
):
    """
    Submit document batch. Per INTAKE_GATEWAY_PLAN Section 3.1.
    """
    resolved_tenant_id = auth.require_tenant_or_bypass(tenant_id, token_tenant_id)
    await ratelimit.check_rate_limit(resolved_tenant_id, limit=100, window_sec=60)

    try:
        manifest_obj = BatchManifest.model_validate_json(manifest)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "MANIFEST_INVALID", "message": str(e)},
        )

    if manifest_obj.tenant_id != tenant_id:
        raise HTTPException(
            status_code=400,
            detail={"code": "MANIFEST_INVALID", "message": "tenant_id in manifest does not match path"},
        )

    if len(manifest_obj.files) != manifest_obj.file_count:
        raise HTTPException(
            status_code=400,
            detail={"code": "MANIFEST_FILE_COUNT_MISMATCH", "message": "file_count does not match files length"},
        )

    file_ids = [f.file_id for f in manifest_obj.files]
    if len(file_ids) != len(set(file_ids)):
        raise HTTPException(
            status_code=400,
            detail={"code": "DUPLICATE_FILE_ID", "message": "Manifest contains duplicate file_id"},
        )

    if len(files) != manifest_obj.file_count:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MANIFEST_FILE_COUNT_MISMATCH",
                "message": f"Uploaded {len(files)} files but manifest expects {manifest_obj.file_count}",
            },
        )

    # Emit batch received event
    await publish_async(
        "INTAKE",
        f"Batch received: {manifest_obj.batch_id} with {manifest_obj.file_count} files",
        "info",
        tenant_id=tenant_id,
    )

    # Build files_by_id: match by order (files[i] -> manifest.files[i])
    files_by_id: dict[str, bytes] = {}
    for i, mf in enumerate(manifest_obj.files):
        if i < len(files):
            content = await files[i].read()
            files_by_id[mf.file_id] = content

    # S3 put - use shared MinIO from main
    from ..main import get_s3, BUCKET

    async def s3_put(key: str, content: bytes) -> None:
        s3 = get_s3()
        bucket = BUCKET or "frostbyte-docs"
        s3.put_object(Bucket=bucket, Key=key, Body=content)
        await publish_async(
            "INTAKE",
            f"Stored to MinIO: {key}",
            "success",
            tenant_id=tenant_id,
        )

    # Emit BATCH_RECEIVED
    await _emit_audit(
        tenant_id=tenant_id,
        event_type="BATCH_RECEIVED",
        resource_id=manifest_obj.batch_id,
        details={"file_count": manifest_obj.file_count, "submitter": manifest_obj.submitter, "component": "intake-gateway"},
    )

    async def emit_audit(tenant_id: str, event_type: str, resource_id: str, details: dict) -> None:
        await _emit_audit(tenant_id=tenant_id, event_type=event_type, resource_id=resource_id, details=details)

    result = await service.process_batch(
        manifest=manifest_obj,
        files_by_id=files_by_id,
        s3_put_fn=s3_put,
        emit_audit_fn=emit_audit,
        store_receipt_fn=receipt_store.store_receipt,
        enqueue_parse_fn=enqueue_parse,
        get_tenant_config_fn=_get_tenant_config,
        malware_scan_fn=_malware_scan,
    )

    # Emit completion event
    await publish_async(
        "INTAKE",
        f"Batch {manifest_obj.batch_id} accepted: {result.accepted} files, {result.rejected} rejected",
        "success" if result.rejected == 0 else "warn",
        tenant_id=tenant_id,
    )

    _batches[manifest_obj.batch_id] = {
        "batch_id": manifest_obj.batch_id,
        "tenant_id": tenant_id,
        "status": "processing",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"success": True, "data": result.model_dump(mode="json")},
    )


@router.get("/{tenant_id}/batch/{batch_id}")
async def get_batch(
    tenant_id: str,
    batch_id: str,
    token_tenant_id: Annotated[str | None, Depends(auth.get_tenant_from_token)] = None,
):
    """Get batch status. Per INTAKE_GATEWAY_PLAN Section 3.2."""
    auth.require_tenant_or_bypass(tenant_id, token_tenant_id)
    batch = _batches.get(batch_id)
    if not batch or batch.get("tenant_id") != tenant_id:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Batch not found"})

    r = batch.get("result")
    if not r:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Batch not found"})

    return {
        "success": True,
        "data": {
            "batch_id": batch_id,
            "tenant_id": tenant_id,
            "status": "processing",
            "submitted_at": batch["submitted_at"],
            "updated_at": batch["updated_at"],
            "summary": {
                "total_files": r.file_count,
                "completed": r.accepted,
                "processing": 0,
                "queued": 0,
                "failed": r.rejected + r.quarantined,
            },
        },
    }


@router.get("/{tenant_id}/receipt/{receipt_id}")
async def get_receipt(
    tenant_id: str,
    receipt_id: str,
    token_tenant_id: Annotated[str | None, Depends(auth.get_tenant_from_token)] = None,
):
    """Get intake receipt. Per INTAKE_GATEWAY_PLAN Section 3.3."""
    auth.require_tenant_or_bypass(tenant_id, token_tenant_id)
    receipt = await receipt_store.load_receipt(tenant_id, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Receipt not found"})

    return {"success": True, "data": receipt.model_dump(mode="json")}
