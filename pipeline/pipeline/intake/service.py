"""
Intake gateway service: process batch, validate, store, emit audit.
Per INTAKE_GATEWAY_PLAN.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from . import validation
from .mime import sniff_mime
from .models import (
    BatchManifest,
    IntakeReceipt,
    BatchReceiptResponse,
    RejectedFile,
    QuarantinedFile,
    ReceiptEntry,
    DEFAULT_MIME_ALLOWLIST,
)


async def process_batch(
    *,
    manifest: BatchManifest,
    files_by_id: dict[str, bytes],
    s3_put_fn,
    emit_audit_fn,
    store_receipt_fn,
    enqueue_parse_fn,
    get_tenant_config_fn,
    malware_scan_fn,
) -> BatchReceiptResponse:
    """
    Process batch: validate each file, store accepted, emit audit, enqueue parse jobs.
    """
    receipts: list[ReceiptEntry] = []
    rejected: list[RejectedFile] = []
    quarantined: list[QuarantinedFile] = []
    accepted = 0

    tenant_id = manifest.tenant_id
    batch_id = manifest.batch_id

    # Load tenant config for mime_allowlist, max_file_size_mb
    try:
        cfg = await get_tenant_config_fn(tenant_id)
        mime_allowlist = frozenset(
            cfg.get("config", {}).get("mime_allowlist") or list(DEFAULT_MIME_ALLOWLIST)
        )
        max_file_size_mb = float(cfg.get("config", {}).get("max_file_size_mb", 500))
    except Exception:
        mime_allowlist = DEFAULT_MIME_ALLOWLIST
        max_file_size_mb = 500.0

    received_at = datetime.now(timezone.utc)

    for mf in manifest.files:
        receipt_id = str(uuid.uuid4())
        content = files_by_id.get(mf.file_id)

        if content is None:
            rejected.append(RejectedFile(
                file_id=mf.file_id,
                reason="CHECKSUM_MISMATCH",
                message="File not found in upload",
            ))
            receipts.append(ReceiptEntry(receipt_id=receipt_id, file_id=mf.file_id, status="rejected"))
            continue

        # Size check
        ok, err = validation.verify_size(len(content), max_file_size_mb)
        if not ok:
            rejected.append(RejectedFile(file_id=mf.file_id, reason="SIZE_EXCEEDED", message=err or ""))
            receipts.append(ReceiptEntry(receipt_id=receipt_id, file_id=mf.file_id, status="rejected"))
            await emit_audit_fn(
                tenant_id=tenant_id,
                event_type="DOCUMENT_REJECTED",
                resource_id=mf.file_id,
                details={"reason": "SIZE_EXCEEDED", "component": "intake-gateway"},
            )
            continue

        # Checksum
        ok, err = validation.verify_checksum(content, mf.sha256)
        if not ok:
            rejected.append(RejectedFile(file_id=mf.file_id, reason="CHECKSUM_MISMATCH", message=err or ""))
            receipts.append(ReceiptEntry(receipt_id=receipt_id, file_id=mf.file_id, status="rejected"))
            await emit_audit_fn(
                tenant_id=tenant_id,
                event_type="DOCUMENT_REJECTED",
                resource_id=mf.file_id,
                details={"reason": "CHECKSUM_MISMATCH", "component": "intake-gateway"},
            )
            continue

        # MIME
        sniffed = sniff_mime(content)
        ok, err = validation.verify_mime(sniffed, mf.mime_type, mime_allowlist)
        if not ok:
            rejected.append(RejectedFile(file_id=mf.file_id, reason="UNSUPPORTED_FORMAT", message=err or ""))
            receipts.append(ReceiptEntry(receipt_id=receipt_id, file_id=mf.file_id, status="rejected"))
            await emit_audit_fn(
                tenant_id=tenant_id,
                event_type="DOCUMENT_REJECTED",
                resource_id=mf.file_id,
                details={"reason": "UNSUPPORTED_FORMAT", "component": "intake-gateway"},
            )
            continue

        # Malware scan (optional)
        scan_result, threat = await malware_scan_fn(content)
        if scan_result == "infected":
            quarantined.append(QuarantinedFile(
                file_id=mf.file_id,
                reason="MALWARE_DETECTED",
                message=threat or "Malware scan flagged file",
            ))
            receipts.append(ReceiptEntry(receipt_id=receipt_id, file_id=mf.file_id, status="quarantined"))
            await emit_audit_fn(
                tenant_id=tenant_id,
                event_type="DOCUMENT_QUARANTINED",
                resource_id=mf.file_id,
                details={"scan_engine": "clamav", "threat_name": threat, "component": "intake-gateway"},
            )
            continue

        # Store in MinIO
        sha256 = validation.compute_sha256(content)
        storage_path = f"raw/{tenant_id}/{mf.file_id}/{sha256}"
        await s3_put_fn(storage_path, content)

        # Store receipt
        receipt = IntakeReceipt(
            receipt_id=receipt_id,
            tenant_id=tenant_id,
            batch_id=batch_id,
            file_id=mf.file_id,
            original_filename=mf.filename,
            mime_type=sniffed,
            size_bytes=len(content),
            sha256=sha256,
            scan_result=scan_result,
            received_at=received_at,
            storage_path=storage_path,
            status="accepted",
        )
        await store_receipt_fn(receipt)

        receipts.append(ReceiptEntry(receipt_id=receipt_id, file_id=mf.file_id, status="accepted"))
        accepted += 1

        await emit_audit_fn(
            tenant_id=tenant_id,
            event_type="DOCUMENT_INGESTED",
            resource_id=mf.file_id,
            details={"sha256": sha256, "mime_type": sniffed, "storage_path": storage_path, "component": "intake-gateway"},
        )

        await enqueue_parse_fn(
            file_id=mf.file_id,
            batch_id=batch_id,
            sha256=sha256,
            storage_path=storage_path,
            tenant_id=tenant_id,
        )

    return BatchReceiptResponse(
        batch_id=batch_id,
        tenant_id=tenant_id,
        file_count=manifest.file_count,
        accepted=accepted,
        rejected=len(rejected),
        quarantined=len(quarantined),
        receipts=receipts,
        rejected_files=rejected,
        quarantined_files=quarantined,
        received_at=received_at,
    )
