#!/usr/bin/env bash

set -e

echo "Running SEZRA smoke test..."

echo "Checking API health..."
health_response="$(curl -s http://localhost:8000/health)"

if [ "$health_response" != '{"status":"ok"}' ]; then
  echo "API health check failed:"
  echo "$health_response"
  exit 1
fi

echo "Running demo scenario..."
./scripts/run-demo-scenario.sh >/tmp/sezra-smoke-test-output.txt

if ! grep -q "Spike anomaly detected" /tmp/sezra-smoke-test-output.txt; then
  echo "Demo scenario did not generate expected analysis:"
  cat /tmp/sezra-smoke-test-output.txt
  exit 1
fi

if ! grep -q "cpu_usage_percent" /tmp/sezra-smoke-test-output.txt; then
  echo "Demo scenario did not include expected semantic context:"
  cat /tmp/sezra-smoke-test-output.txt
  exit 1
fi

echo "SEZRA smoke test passed."