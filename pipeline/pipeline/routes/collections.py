"""
Collection query API with optional multimodal query_file.
Reference: Enhancement #9 PRD, OpenAPI /collections/{name}/query.
"""
from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..embedding import get_text_embedding
from ..multimodal import detect_modality
from ..multimodal.audio_processor import _get_whisper_model
from ..multimodal.image_processor import _get_clip_model
from ..vector_store import search_qdrant

router = APIRouter(prefix="/api/v1/collections", tags=["collections"])
TENANT_DEFAULT = os.getenv("TENANT_DEFAULT", "default")


@router.post("/{name}/query")
async def query_collection(
    name: str,
    vector: str | None = Form(None, description="JSON array of floats, e.g. [0.1, 0.2, ...]"),
    query_file: UploadFile | None = File(None),
    top_k: int = Form(10),
    tenant_id: str = Form(default=TENANT_DEFAULT),
) -> dict[str, Any]:
    """
    Query collection by vector or by file (image/audio/video).
    If query_file provided, derive vector from it (CLIP for image, Whisper+embed for audio/video).
    """
    if query_file is not None:
        content = await query_file.read()
        filename = query_file.filename or "query"
        modality = detect_modality(filename)
        if modality == "image":
            from PIL import Image
            image = Image.open(io.BytesIO(content)).convert("RGB")
            clip = _get_clip_model()
            vector = clip.encode(image).tolist()
        elif modality == "audio":
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix or "") as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            try:
                model = _get_whisper_model()
                result = model.transcribe(tmp_path)
                transcript = result.get("text", "")
                vector = await get_text_embedding(transcript)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        elif modality == "video":
            import ffmpeg
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix or ".mp4") as tmp:
                tmp.write(content)
                video_path = tmp.name
            audio_path = video_path + ".wav"
            try:
                (ffmpeg.input(video_path).output(audio_path, acodec="pcm_s16le", ar=16000).overwrite_output().run(quiet=True))
                model = _get_whisper_model()
                result = model.transcribe(audio_path)
                transcript = result.get("text", "")
                vector = await get_text_embedding(transcript)
            finally:
                for p in (video_path, audio_path):
                    if os.path.exists(p):
                        try:
                            os.unlink(p)
                        except OSError:
                            pass
        else:
            raise HTTPException(status_code=400, detail="Unsupported query file type; use image, audio, or video")
    elif vector is not None:
        try:
            vector = json.loads(vector)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="vector must be a valid JSON array")

    if vector is None:
        raise HTTPException(status_code=400, detail="Either vector or query_file must be provided")

    results = await search_qdrant(tenant_id=tenant_id, vector=vector, top_k=top_k)
    return {"results": results}
