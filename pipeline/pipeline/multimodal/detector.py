"""
Modality detection and routing by file extension.
Reference: Enhancement #9 PRD - Multi-Modal Document Support.
"""
from __future__ import annotations

from pathlib import Path

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".gif"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}
VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def detect_modality(filename: str) -> str:
    """Determine modality from filename extension. Returns 'image', 'audio', 'video', or 'text'."""
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    elif ext in AUDIO_EXT:
        return "audio"
    elif ext in VIDEO_EXT:
        return "video"
    else:
        return "text"
