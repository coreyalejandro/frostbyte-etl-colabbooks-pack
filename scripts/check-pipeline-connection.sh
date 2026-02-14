#!/bin/bash
# Pipeline Connection Diagnostic Script
# Run this to diagnose why the Pipeline Log shows "DISCONNECTED"

set -e

echo "==================================="
echo "Pipeline Connection Diagnostics"
echo "==================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $name... "
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        return 1
    fi
}

# 1. Check Infrastructure Services
echo "1. Checking Infrastructure Services"
echo "-----------------------------------"

# Redis
echo -n "Checking Redis... "
if redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC} - Run: docker-compose up -d redis"
fi

# PostgreSQL
echo -n "Checking PostgreSQL... "
if pg_isready -h localhost -p 5433 -U frostbyte 2>/dev/null | grep -q "accepting connections"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC} - Run: docker-compose up -d postgres"
fi

# MinIO
check_service "MinIO" "http://localhost:9000/minio/health/live" "200"

# Qdrant
check_service "Qdrant" "http://localhost:6333/readyz" "200"

echo ""

# 2. Check Pipeline API
echo "2. Checking Pipeline API"
echo "------------------------"

check_service "Pipeline API" "http://localhost:8000/health" "200"

echo ""

# 3. Check SSE Endpoint
echo "3. Checking SSE Stream Endpoint"
echo "--------------------------------"
echo -n "Checking SSE endpoint... "
if curl -s -N http://localhost:8000/api/v1/pipeline/stream 2>&1 | head -1 | grep -q "data:"; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}MAYBE OK${NC} - Testing with timeout..."
    timeout 2 curl -s -N http://localhost:8000/api/v1/pipeline/stream &
    sleep 1
    echo -e "${YELLOW}SSE endpoint responded (may need browser test)${NC}"
fi

echo ""

# 4. Summary
echo "==================================="
echo "Summary"
echo "==================================="
echo ""

if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}Pipeline API is running.${NC}"
    echo "If the dashboard still shows DISCONNECTED:"
    echo "  1. Check browser console for CORS errors"
    echo "  2. Verify you're logged in to the admin dashboard"
    echo "  3. Try refreshing the page"
else
    echo -e "${RED}Pipeline API is NOT running.${NC}"
    echo ""
    echo "To start the services:"
    echo "  1. Start infrastructure: docker-compose up -d"
    echo "  2. Start Pipeline API:"
    echo "     cd pipeline"
    echo "     pip install -e ."
    echo "     uvicorn pipeline.main:app --reload --port 8000"
    echo ""
    echo "Environment variables needed:"
    echo "  - REDIS_URL=redis://localhost:6379/0"
    echo "  - FROSTBYTE_AUTH_BYPASS=true  (for local dev)"
fi

echo ""
