"""
Audio processing: transcription via Whisper.
Reference: Enhancement #9 PRD.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import whisper

from .config import WHISPER_MODEL

_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(WHISPER_MODEL)
    return _whisper_model


async def process_audio(content: bytes, filename: str) -> dict:
    """
    Transcribe audio with Whisper. Returns {transcript, modality}.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix or "") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        model = _get_whisper_model()
        result = model.transcribe(tmp_path)
        transcript = result.get("text", "")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return {"transcript": transcript, "modality": "audio"}
