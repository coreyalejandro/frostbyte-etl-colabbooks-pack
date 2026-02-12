"""
Multimodal-specific configuration.
Reference: Enhancement #9 PRD.
"""
from __future__ import annotations

import os

TESSERACT_CMD = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny.en")
CLIP_MODEL_NAME = os.getenv("CLIP_MODEL_NAME", "sentence-transformers/clip-ViT-B-32")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "/usr/bin/ffmpeg")
