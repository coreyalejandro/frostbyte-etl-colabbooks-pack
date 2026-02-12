# Frostbyte ETL Pipeline — Multi-modal support (Enhancement #9)
# Tesseract, FFmpeg for OCR, transcription, video frame extraction
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pipeline/ pipeline/

RUN pip install --no-cache-dir -e ./pipeline

EXPOSE 8000
CMD ["uvicorn", "pipeline.main:app", "--host", "0.0.0.0", "--port", "8000"]
