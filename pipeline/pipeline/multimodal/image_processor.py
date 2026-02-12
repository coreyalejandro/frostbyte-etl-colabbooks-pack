"""
Image processing: OCR (Tesseract) + CLIP embeddings.
Reference: Enhancement #9 PRD.
"""
from __future__ import annotations

import io

import pytesseract
from PIL import Image
from sentence_transformers import SentenceTransformer

from .config import CLIP_MODEL_NAME, TESSERACT_CMD

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Lazy-load CLIP model
_clip_model: SentenceTransformer | None = None


def _get_clip_model() -> SentenceTransformer:
    global _clip_model
    if _clip_model is None:
        _clip_model = SentenceTransformer(CLIP_MODEL_NAME)
    return _clip_model


async def process_image(content: bytes, filename: str) -> dict:
    """
    Extract OCR text and CLIP embedding from image.
    Returns: {ocr_text, embedding, modality}
    """
    image = Image.open(io.BytesIO(content)).convert("RGB")
    ocr_text = pytesseract.image_to_string(image)
    clip = _get_clip_model()
    embedding = clip.encode(image).tolist()
    return {
        "ocr_text": ocr_text,
        "embedding": embedding,
        "modality": "image",
    }
