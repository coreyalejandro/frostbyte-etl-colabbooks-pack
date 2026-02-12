-- Migration: Intake receipts table per INTAKE_GATEWAY_PLAN Section 8
-- Created: 2026-02-11

CREATE TABLE IF NOT EXISTS intake_receipts (
    receipt_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    file_id TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    sha256 TEXT NOT NULL,
    scan_result TEXT NOT NULL CHECK (scan_result IN ('clean', 'quarantined', 'skipped')),
    received_at TIMESTAMPTZ NOT NULL,
    storage_path TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('accepted', 'rejected', 'quarantined')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intake_receipts_tenant_batch
ON intake_receipts (tenant_id, batch_id);

CREATE INDEX IF NOT EXISTS idx_intake_receipts_tenant_created
ON intake_receipts (tenant_id, created_at DESC);
