"""
Video processing: audio extraction + transcription, frame extraction + OCR + CLIP.
Reference: Enhancement #9 PRD.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import cv2
import ffmpeg
import pytesseract
from PIL import Image
from sentence_transformers import SentenceTransformer

from .audio_processor import _get_whisper_model
from .config import TESSERACT_CMD
from .image_processor import _get_clip_model

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


async def process_video(content: bytes, filename: str) -> dict:
    """
    Extract audio transcript and frame OCR+CLIP. Returns {transcript, frames, modality}.
    Frames at 1 fps.
    """
    ext = Path(filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        video_path = tmp.name

    frames_data: list[dict] = []
    transcript = ""

    try:
        # 1. Extract audio and transcribe
        audio_path = video_path + ".wav"
        try:
            (ffmpeg.input(video_path).output(audio_path, acodec="pcm_s16le", ar=16000).overwrite_output().run(quiet=True))
            whisper_model = _get_whisper_model()
            audio_result = whisper_model.transcribe(audio_path)
            transcript = audio_result.get("text", "")
        except Exception:
            pass
        finally:
            if os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass

        # 2. Extract frames at 1 fps
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 1.0
        frame_interval = max(1, int(fps))
        frame_count = 0
        clip_model: SentenceTransformer = _get_clip_model()

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % frame_interval == 0:
                timestamp = float(frame_count) / fps
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                frame_text = pytesseract.image_to_string(pil_img)
                embedding = clip_model.encode(pil_img).tolist()
                frames_data.append({
                    "timestamp": timestamp,
                    "ocr_text": frame_text,
                    "embedding": embedding,
                })
            frame_count += 1
        cap.release()
    finally:
        try:
            os.unlink(video_path)
        except OSError:
            pass

    return {
        "transcript": transcript,
        "frames": frames_data,
        "modality": "video",
    }
