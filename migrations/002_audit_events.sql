-- Migration 002: Audit events (append-only, immutable)
-- Created: 2026-02-11
-- Reference: docs/AUDIT_ARCHITECTURE.md Section 2.3, docs/FOUNDATION_LAYER_PLAN.md Section 3.3

-- Audit events table (append-only)
CREATE TABLE IF NOT EXISTS audit_events (
  event_id       UUID PRIMARY KEY,
  tenant_id      TEXT NOT NULL,
  event_type     TEXT NOT NULL,
  timestamp      TIMESTAMPTZ NOT NULL,
  actor          TEXT,
  resource_type  TEXT NOT NULL,
  resource_id    TEXT NOT NULL,
  details        JSONB NOT NULL,
  previous_event_id UUID REFERENCES audit_events(event_id)
);

-- Indexes for query patterns (AUDIT_ARCHITECTURE Section 2.3)
CREATE INDEX IF NOT EXISTS idx_audit_tenant_timestamp ON audit_events (tenant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_tenant_resource_timestamp ON audit_events (tenant_id, resource_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_event_type_timestamp ON audit_events (event_type, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_previous_event ON audit_events (previous_event_id) WHERE previous_event_id IS NOT NULL;

-- Create roles for production (idempotent; no-op if exist)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'frostbyte_app') THEN
    CREATE ROLE frostbyte_app NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'frostbyte_auditor') THEN
    CREATE ROLE frostbyte_auditor NOLOGIN;
  END IF;
END
$$;

-- Append-only: application can INSERT/SELECT only; auditor SELECT only
GRANT INSERT, SELECT ON audit_events TO frostbyte_app;
REVOKE UPDATE, DELETE ON audit_events FROM frostbyte_app;
GRANT SELECT ON audit_events TO frostbyte_auditor;

-- Trigger to block UPDATE/DELETE (defense in depth)
CREATE OR REPLACE FUNCTION block_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_events is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_events_no_update_delete ON audit_events;
CREATE TRIGGER audit_events_no_update_delete
  BEFORE UPDATE OR DELETE ON audit_events
  FOR EACH ROW
  EXECUTE FUNCTION block_audit_modification();
