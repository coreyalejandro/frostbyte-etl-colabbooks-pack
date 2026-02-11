#!/bin/bash
set -e

echo "Validating OpenAPI spec..."

# Check if openapi.yaml exists
if [ ! -f "../../docs/api/openapi.yaml" ]; then
    echo "ERROR: docs/api/openapi.yaml not found"
    exit 1
fi

# Validate JSON structure
if ! python3 -c "import json, sys; json.load(open('../../docs/api/openapi.yaml'))" 2>/dev/null; then
    echo "ERROR: openapi.yaml is not valid JSON"
    exit 1
fi

echo "OpenAPI spec is valid"
exit 0
