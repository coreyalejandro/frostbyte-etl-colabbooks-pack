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
from ..events import publish_async

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# Lazy-load CLIP model
_clip_model: SentenceTransformer | None = None


def _get_clip_model() -> SentenceTransformer:
    global _clip_model
    if _clip_model is None:
        _clip_model = SentenceTransformer(CLIP_MODEL_NAME)
    return _clip_model


async def process_image(
    content: bytes, 
    filename: str,
    document_id: str | None = None,
    tenant_id: str | None = None,
) -> dict:
    """
    Extract OCR text and CLIP embedding from image.
    Returns: {ocr_text, embedding, modality}
    """
    await publish_async(
        "MULTIMODAL",
        f"Processing image: {filename}",
        "info",
        document_id=document_id,
        tenant_id=tenant_id,
    )
    
    try:
        image = Image.open(io.BytesIO(content)).convert("RGB")
        
        # OCR
        await publish_async(
            "MULTIMODAL",
            f"Running OCR on {filename}",
            "info",
            document_id=document_id,
            tenant_id=tenant_id,
        )
        ocr_text = pytesseract.image_to_string(image)
        
        # CLIP embedding
        await publish_async(
            "MULTIMODAL",
            f"Generating CLIP embedding for {filename}",
            "info",
            document_id=document_id,
            tenant_id=tenant_id,
        )
        clip = _get_clip_model()
        embedding = clip.encode(image).tolist()
        
        await publish_async(
            "MULTIMODAL",
            f"Image processing complete: {len(ocr_text)} chars OCR, {len(embedding)}d embedding",
            "success",
            document_id=document_id,
            tenant_id=tenant_id,
        )
        
        return {
            "ocr_text": ocr_text,
            "embedding": embedding,
            "modality": "image",
        }
    except Exception as e:
        await publish_async(
            "MULTIMODAL",
            f"Image processing failed: {e}",
            "error",
            document_id=document_id,
            tenant_id=tenant_id,
        )
        raise
