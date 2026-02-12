"""
Intake validation: MIME, checksum, size per INTAKE_GATEWAY_PLAN Section 2.3, 5.
"""
from __future__ import annotations

import hashlib
from typing import Literal

from .models import DEFAULT_MIME_ALLOWLIST

RejectReason = Literal["UNSUPPORTED_FORMAT", "SIZE_EXCEEDED", "CHECKSUM_MISMATCH"]


def compute_sha256(content: bytes) -> str:
    """Compute SHA-256 hex digest of file content."""
    return hashlib.sha256(content).hexdigest()


def verify_checksum(content: bytes, expected_sha256: str) -> tuple[bool, str | None]:
    """
    Verify file content matches manifest SHA-256.
    Returns (ok, error_message). Ok=True means match.
    """
    computed = compute_sha256(content)
    if computed.lower() != expected_sha256.lower():
        return False, f"Expected SHA-256 {expected_sha256[:16]}... but computed {computed[:16]}..."
    return True, None


def verify_size(size_bytes: int, max_mb: float = 500) -> tuple[bool, str | None]:
    """Verify file size within limit. max_mb from tenant config."""
    max_bytes = int(max_mb * 1024 * 1024)
    if size_bytes > max_bytes:
        return False, f"File size {size_bytes} exceeds max {max_bytes} bytes ({max_mb} MB)"
    return True, None


def verify_mime(
    sniffed_mime: str,
    declared_mime: str | None,
    allowlist: set[str] | frozenset[str] | None = None,
) -> tuple[bool, str | None]:
    """
    Verify MIME against allowlist. If declared differs from sniffed, reject (spoofing).
    Returns (ok, error_message).
    """
    allowed = allowlist or DEFAULT_MIME_ALLOWLIST
    if sniffed_mime not in allowed:
        return False, f"MIME type {sniffed_mime} is not on the allowlist"
    if declared_mime and declared_mime != sniffed_mime:
        return False, (
            f"Declared MIME {declared_mime} differs from sniffed {sniffed_mime} (possible spoofing)"
        )
    return True, None
