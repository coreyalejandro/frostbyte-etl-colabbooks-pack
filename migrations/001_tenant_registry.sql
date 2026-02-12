-- Migration 001: Tenant registry (control-plane database)
-- Created: 2026-02-11
-- Reference: docs/FOUNDATION_LAYER_PLAN.md Section 1.1, docs/PRD.md Section 3

-- Tenant registry (control-plane database)
CREATE TABLE IF NOT EXISTS tenants (
  tenant_id                TEXT PRIMARY KEY,
  state                    TEXT NOT NULL CHECK (state IN (
    'PENDING', 'PROVISIONING', 'ACTIVE', 'SUSPENDED',
    'DEPROVISIONING', 'DEPROVISIONED', 'FAILED'
  )),
  config                   JSONB NOT NULL,
  config_version           INTEGER NOT NULL DEFAULT 1,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  provisioning_started_at  TIMESTAMPTZ,
  provisioned_at           TIMESTAMPTZ,
  age_public_key           TEXT,
  endpoints                JSONB
);

-- State transitions: PRD Section 3.1
COMMENT ON COLUMN tenants.state IS 'Tenant state machine; see PRD Section 3.1';
COMMENT ON COLUMN tenants.config IS 'Per-tenant configuration per PRD Appendix G';
COMMENT ON COLUMN tenants.config_version IS 'Incremented on every config change';
COMMENT ON COLUMN tenants.provisioning_started_at IS 'Set when state -> PROVISIONING';
COMMENT ON COLUMN tenants.provisioned_at IS 'Set when state -> ACTIVE';
COMMENT ON COLUMN tenants.age_public_key IS 'age public key for SOPS decryption; see TENANT_ISOLATION_STORAGE_ENCRYPTION Section 6';
COMMENT ON COLUMN tenants.endpoints IS 'JSON: {"api_url":"...","health_url":"..."}';

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tenants_state ON tenants (state);
CREATE INDEX IF NOT EXISTS idx_tenants_created_at ON tenants (created_at);
CREATE INDEX IF NOT EXISTS idx_tenants_config ON tenants USING GIN (config);

-- Trigger to maintain updated_at
CREATE OR REPLACE FUNCTION tenants_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tenants_updated_at_trigger ON tenants;
CREATE TRIGGER tenants_updated_at_trigger
  BEFORE UPDATE ON tenants
  FOR EACH ROW
  EXECUTE FUNCTION tenants_updated_at();
