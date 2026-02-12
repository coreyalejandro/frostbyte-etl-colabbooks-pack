"""
MIME type sniffing via python-magic (libmagic) per INTAKE_GATEWAY_PLAN Section 5.
"""
from __future__ import annotations

try:
    import magic
except ImportError:
    magic = None  # type: ignore


def sniff_mime(content: bytes) -> str:
    """
    Sniff MIME type from content. Uses python-magic (libmagic).
    Falls back to application/octet-stream if magic not available.
    """
    if magic is None:
        return "application/octet-stream"
    m = magic.Magic(mime=True)
    return m.from_buffer(content) or "application/octet-stream"
