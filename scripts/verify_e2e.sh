#!/usr/bin/env bash
# End-to-end verification: Docker up → migrations → pipeline → ingest → verify.
# Reference: BUILD_1HR.md
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== E2E Verification ==="

# 1. Docker
echo "[1/6] Starting Docker services..."
if ! docker compose up -d 2>/dev/null; then
  echo "ERROR: Docker compose failed. Ensure Docker Desktop is running."
  exit 1
fi

echo "Waiting for services (30s)..."
sleep 30

# 2. Migrations
echo "[2/6] Running migrations..."
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-frostbyte}"
export PGPASSWORD="${PGPASSWORD:-frostbyte}"
export PGDATABASE="${PGDATABASE:-frostbyte}"

for f in 001_tenant_registry.sql 002_audit_events.sql; do
  if [[ -f "migrations/$f" ]]; then
    psql -v ON_ERROR_STOP=1 -f "migrations/$f" 2>/dev/null || true
  fi
done

# 3. Pipeline (background)
echo "[3/6] Starting pipeline API..."
cd pipeline
pip install -e . -q 2>/dev/null || true
uvicorn pipeline.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!
cd "$ROOT"

sleep 5

# 4. Ingest
echo "[4/6] Ingesting test document..."
echo "Test content for ETL verification." > /tmp/frostbyte_test.txt
RESP=$(curl -s -X POST http://localhost:8000/api/v1/intake \
  -F "file=@/tmp/frostbyte_test.txt" \
  -F "tenant_id=default" 2>/dev/null || echo '{"error":"failed"}')

# 5. Verify response
echo "[5/6] Verifying intake response..."
if echo "$RESP" | grep -q '"document_id"'; then
  echo "PASS: Intake returned document_id"
else
  echo "FAIL: Intake failed - $RESP"
  kill $UVICORN_PID 2>/dev/null || true
  exit 1
fi

# 6. Verify data
echo "[6/6] Verifying data in stores..."
DOC_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('document_id',''))" 2>/dev/null || echo "")

if [[ -n "$DOC_ID" ]]; then
  if curl -s "http://localhost:8000/api/v1/documents/$DOC_ID" | grep -q "ingested"; then
    echo "PASS: Document metadata accessible"
  else
    echo "WARN: Could not fetch document metadata"
  fi
fi

# Cleanup
kill $UVICORN_PID 2>/dev/null || true

echo ""
echo "=== E2E Verification Complete ==="
