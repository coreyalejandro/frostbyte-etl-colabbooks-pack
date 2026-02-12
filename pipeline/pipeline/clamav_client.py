"""
ClamAV malware scanning via clamd socket per TECH_DECISIONS #32.
Falls back to 'clean' when ClamAV unavailable (dev mode).
"""
from __future__ import annotations

import io
import os

_clamd = None


def _get_clamd():
    global _clamd
    if _clamd is not None:
        return _clamd
    try:
        import clamd

        sock = os.getenv("CLAMAV_SOCKET", "/var/run/clamav/clamd.sock")
        host = os.getenv("CLAMAV_HOST", "localhost")
        port = int(os.getenv("CLAMAV_PORT", "3310"))

        if sock and os.path.exists(sock):
            cd = clamd.ClamdUnixSocket(socket_path=sock)
        else:
            cd = clamd.ClamdNetworkSocket(host=host, port=port)
        cd.ping()
        _clamd = cd
        return cd
    except Exception:
        _clamd = False
        return None


def scan_bytes(content: bytes) -> tuple[str, str | None]:
    """
    Scan content via clamd instream.
    Returns (result, threat_name). result is 'clean' or 'infected'.
    When ClamAV unavailable, returns ('clean', None).
    """
    cd = _get_clamd()
    if cd is None:
        return "clean", None

    try:
        buf = io.BytesIO(content)
        result = cd.instream(buf)
        stream_val = result.get("stream")
        if isinstance(stream_val, tuple) and len(stream_val) >= 2 and stream_val[0] == "FOUND":
            return "infected", str(stream_val[1])
        return "clean", None
    except Exception:
        return "skipped", None  # Service unavailable
