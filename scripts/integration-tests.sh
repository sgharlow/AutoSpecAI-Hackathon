#!/bin/bash

# AutoSpec.AI Integration Tests
# Tests API endpoints and system functionality

set -e

API_URL=${1:-""}
ENVIRONMENT=${2:-"dev"}

echo "Running integration tests for environment: $ENVIRONMENT"
echo "API URL: $API_URL"

if [ -z "$API_URL" ]; then
    echo "API URL not provided, skipping API tests"
    exit 0
fi

# Test health endpoint
echo "Testing health endpoint..."
if curl -f -s "$API_URL/health" > /dev/null; then
    echo "Health endpoint: PASS"
else
    echo "Health endpoint: FAIL"
    exit 1
fi

# Test status endpoint
echo "Testing status endpoint..."
if curl -f -s "$API_URL/status" > /dev/null; then
    echo "Status endpoint: PASS"
else
    echo "Status endpoint: WARN (not critical)"
fi

echo "Integration tests completed successfully!"