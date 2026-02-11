-- Migration: Add custom metadata column to documents table
-- Created: 2026-02-11

-- Add custom_metadata JSONB column with GIN index for query performance
ALTER TABLE documents ADD COLUMN IF NOT EXISTS custom_metadata JSONB DEFAULT '{}';

-- Create GIN index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_documents_custom_metadata 
ON documents USING GIN (custom_metadata);

-- Create index on tenant_id + custom_metadata for tenant-scoped queries
CREATE INDEX IF NOT EXISTS idx_documents_tenant_custom_metadata 
ON documents (tenant_id, custom_metadata) WHERE custom_metadata <> '{}';
