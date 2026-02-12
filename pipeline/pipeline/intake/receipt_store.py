"""
PostgreSQL receipt persistence per INTAKE_GATEWAY_PLAN Section 8.
"""
from __future__ import annotations

from .models import IntakeReceipt


async def store_receipt(receipt: IntakeReceipt) -> None:
    """Persist intake receipt to PostgreSQL."""
    from .. import db

    pool = db._get_pool()
    await pool.execute(
        """
        INSERT INTO intake_receipts (
            receipt_id, tenant_id, batch_id, file_id, original_filename,
            mime_type, size_bytes, sha256, scan_result, received_at,
            storage_path, status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (receipt_id) DO NOTHING
        """,
        receipt.receipt_id,
        receipt.tenant_id,
        receipt.batch_id,
        receipt.file_id,
        receipt.original_filename,
        receipt.mime_type,
        receipt.size_bytes,
        receipt.sha256,
        receipt.scan_result,
        receipt.received_at,
        receipt.storage_path,
        receipt.status,
    )


async def load_receipt(tenant_id: str, receipt_id: str) -> IntakeReceipt | None:
    """Load intake receipt by tenant and receipt_id."""
    from .. import db

    pool = db._get_pool()
    row = await pool.fetchrow(
        """
        SELECT receipt_id, tenant_id, batch_id, file_id, original_filename,
               mime_type, size_bytes, sha256, scan_result, received_at,
               storage_path, status
        FROM intake_receipts
        WHERE tenant_id = $1 AND receipt_id = $2
        """,
        tenant_id,
        receipt_id,
    )
    if row is None:
        return None
    return IntakeReceipt(
        receipt_id=row["receipt_id"],
        tenant_id=row["tenant_id"],
        batch_id=row["batch_id"],
        file_id=row["file_id"],
        original_filename=row["original_filename"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        sha256=row["sha256"],
        scan_result=row["scan_result"],
        received_at=row["received_at"],
        storage_path=row["storage_path"],
        status=row["status"],
    )
