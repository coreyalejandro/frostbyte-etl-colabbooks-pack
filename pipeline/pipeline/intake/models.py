"""
Intake gateway Pydantic models per INTAKE_GATEWAY_PLAN.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# Default MIME allowlist per PRD Appendix C, INTAKE_GATEWAY_PLAN Section 5
DEFAULT_MIME_ALLOWLIST = frozenset([
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
    "image/png",
    "image/tiff",
])


class ManifestFile(BaseModel):
    """Single file entry in batch manifest."""

    file_id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str


class BatchManifest(BaseModel):
    """Batch manifest per INTAKE_GATEWAY_PLAN Section 2.2."""

    batch_id: str
    tenant_id: str
    file_count: int
    files: list[ManifestFile]
    submitted_at: str | None = None
    submitter: str | None = None


class IntakeReceipt(BaseModel):
    """Immutable intake receipt per INTAKE_GATEWAY_PLAN Section 8."""

    receipt_id: str
    tenant_id: str
    batch_id: str
    file_id: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    scan_result: Literal["clean", "quarantined", "skipped"]
    received_at: datetime
    storage_path: str
    status: Literal["accepted", "rejected", "quarantined"]


class RejectedFile(BaseModel):
    """Per-file reject entry in batch response."""

    file_id: str
    reason: Literal["UNSUPPORTED_FORMAT", "SIZE_EXCEEDED", "CHECKSUM_MISMATCH"]
    message: str


class QuarantinedFile(BaseModel):
    """Per-file quarantine entry in batch response."""

    file_id: str
    reason: Literal["MALWARE_DETECTED"]
    message: str


class ReceiptEntry(BaseModel):
    """Receipt summary in batch response."""

    receipt_id: str
    file_id: str
    status: Literal["accepted", "rejected", "quarantined"]


class BatchReceiptResponse(BaseModel):
    """202 Accepted batch receipt per INTAKE_GATEWAY_PLAN Section 3.1."""

    batch_id: str
    tenant_id: str
    file_count: int
    accepted: int
    rejected: int
    quarantined: int
    receipts: list[ReceiptEntry]
    rejected_files: list[RejectedFile] = Field(default_factory=list)
    quarantined_files: list[QuarantinedFile] = Field(default_factory=list)
    received_at: datetime
