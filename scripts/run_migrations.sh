#!/usr/bin/env bash
# Run control-plane migrations in order.
# Reference: docs/FOUNDATION_LAYER_PLAN.md Section 3.2
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MIGRATIONS_DIR="$ROOT/migrations"

# Default: local PostgreSQL
export PGHOST="${PGHOST:-127.0.0.1}"
export PGPORT="${PGPORT:-5433}"
export PGUSER="${PGUSER:-frostbyte}"
export PGPASSWORD="${PGPASSWORD:-frostbyte}"
export PGDATABASE="${PGDATABASE:-frostbyte}"

# Or use FROSTBYTE_CONTROL_DB_URL to parse connection string
if [[ -n "${FROSTBYTE_CONTROL_DB_URL:-}" ]]; then
  # Parse postgresql://user:pass@host:port/db
  if [[ "$FROSTBYTE_CONTROL_DB_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
    export PGUSER="${BASH_REMATCH[1]}"
    export PGPASSWORD="${BASH_REMATCH[2]}"
    export PGHOST="${BASH_REMATCH[3]}"
    export PGPORT="${BASH_REMATCH[4]}"
    export PGDATABASE="${BASH_REMATCH[5]}"
  fi
fi

echo "Running migrations from $MIGRATIONS_DIR"
echo "Target: $PGUSER@$PGHOST:$PGPORT/$PGDATABASE"

for f in 001_tenant_registry.sql 002_audit_events.sql 005_intake_receipts.sql 006_tenant_schemas.sql 007_add_multimodal_support.sql; do
  path="$MIGRATIONS_DIR/$f"
  if [[ -f "$path" ]]; then
    echo "  Applying $f"
    psql -v ON_ERROR_STOP=1 -f "$path"
  fi
done

echo "Migrations complete."
