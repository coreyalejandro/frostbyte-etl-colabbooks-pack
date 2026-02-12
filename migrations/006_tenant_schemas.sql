-- Migration 006: Tenant-configurable schema extensions for document and chunk metadata
-- Created: 2026-02-12
-- Reference: Enhancement #4 PRD - Configurable Schema Extensions

CREATE TABLE IF NOT EXISTS tenant_schemas (
    tenant_id       TEXT PRIMARY KEY,
    document_fields JSONB NOT NULL DEFAULT '{}',
    chunk_fields    JSONB NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tenant_schemas_updated_at ON tenant_schemas (updated_at);

COMMENT ON TABLE tenant_schemas IS 'Per-tenant JSON Schema definitions for custom document and chunk metadata';
COMMENT ON COLUMN tenant_schemas.document_fields IS 'JSON Schema (draft-07) for custom document metadata';
COMMENT ON COLUMN tenant_schemas.chunk_fields IS 'JSON Schema (draft-07) for custom chunk metadata';
