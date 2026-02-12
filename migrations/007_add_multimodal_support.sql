-- Migration 007: Multi-modal document support
-- Created: 2026-02-12
-- Reference: Enhancement #9 PRD - Multi-Modal Document Support
--
-- Prerequisites: pgvector extension (e.g. use ankane/pgvector Docker image or
-- install https://github.com/pgvector/pgvector in your PostgreSQL).
-- Documents and chunks tables are created here for multimodal pipeline.

CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table (if not exists from prior migrations)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    modality TEXT NOT NULL DEFAULT 'text' CHECK (modality IN ('text', 'image', 'audio', 'video')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents (tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status);

-- Chunks table (if not exists)
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT,
    embedding vector(768),  -- Nomic text embeddings
    modality TEXT NOT NULL DEFAULT 'text' CHECK (modality IN (
        'text', 'image_text', 'image_embedding', 'audio_transcript',
        'video_frame_text', 'video_frame_embedding', 'video_transcript'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_modality ON chunks (modality);

-- Add modality column if chunks already existed without it (idempotent)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chunks')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chunks' AND column_name = 'modality')
    THEN
        ALTER TABLE chunks ADD COLUMN modality TEXT NOT NULL DEFAULT 'text';
    END IF;
END $$;

-- Image embeddings table (CLIP 512d)
CREATE TABLE IF NOT EXISTS image_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    embedding vector(512) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_embeddings_chunk_id ON image_embeddings (chunk_id);

-- Video frames metadata table
CREATE TABLE IF NOT EXISTS video_frames (
    frame_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    timestamp_sec FLOAT NOT NULL,
    frame_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_video_frames_chunk_id ON video_frames (chunk_id);

COMMENT ON TABLE documents IS 'Document metadata per Enhancement #9 multimodal PRD';
COMMENT ON TABLE chunks IS 'Text/image/audio/video chunks with embeddings';
COMMENT ON TABLE image_embeddings IS 'CLIP image embeddings (512d) for hybrid search';
COMMENT ON TABLE video_frames IS 'Video frame metadata with timestamps';
