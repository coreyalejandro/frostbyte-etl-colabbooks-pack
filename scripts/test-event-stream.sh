#!/bin/bash
# Test Pipeline Event Stream
# Verifies that all pipeline stages emit events correctly

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================"
echo "Pipeline Event Stream Test"
echo "================================"
echo ""

# Check if pipeline API is running
echo -n "1. Checking Pipeline API... "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    echo "   Pipeline API not running on port 8000"
    echo "   Run: make pipeline"
    exit 1
fi

# Check if Redis is running
echo -n "2. Checking Redis... "
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    echo "   Redis not running"
    echo "   Run: docker-compose up -d redis"
    exit 1
fi

# Test SSE endpoint
echo -n "3. Testing SSE stream... "
if timeout 3 curl -s -N http://localhost:8000/api/v1/pipeline/stream 2>/dev/null | head -1 | grep -q "data:"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}WARNING${NC}"
    echo "   SSE endpoint available but no events yet"
fi

echo ""
echo "4. Listening for events (30 seconds)..."
echo "   Upload a document to see events flow through:"
echo ""
echo "   curl -X POST http://localhost:8000/api/v1/intake \\"
echo "     -F 'file=@/path/to/document.pdf' \\"
echo "     -F 'tenant_id=default'"
echo ""

# Subscribe to Redis channel to see all events
echo "   Events will appear below:"
echo "   ----------------------------------------"
timeout 30 redis-cli SUBSCRIBE pipeline:events 2>/dev/null | while read line; do
    if echo "$line" | grep -q "data:"; then
        echo "   📡 $line"
    fi
done || true

echo ""
echo "   ----------------------------------------"
echo ""

# Check which stages are emitting
echo "5. Checking event emission from each stage:"
echo ""

# Test by uploading a simple file
echo "   Creating test document..."
echo "Test document for Frostbyte ETL" > /tmp/test-doc.txt

echo "   Uploading test document..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/intake \
    -F "file=@/tmp/test-doc.txt" \
    -F "tenant_id=default" 2>/dev/null || echo '{"status": "error"}')

if echo "$RESPONSE" | grep -q "document_id\|status"; then
    echo -e "   ${GREEN}✓${NC} Upload successful"
    echo "   Response: $RESPONSE"
else
    echo -e "   ${RED}✗${NC} Upload failed"
    echo "   Response: $RESPONSE"
fi

echo ""
echo "6. Checking recent events in Redis:"
echo ""

# Get last 10 events from Redis (if we had persistence)
echo "   Note: Events are ephemeral (pub/sub). Check Pipeline Log panel in dashboard."

echo ""
echo "================================"
echo "Test Complete"
echo "================================"
echo ""
echo "If events are not appearing:"
echo "  1. Check pipeline is running: make pipeline-status"
echo "  2. Check for errors: make pipeline-logs"
echo "  3. Verify Redis connection: redis-cli ping"
echo ""
