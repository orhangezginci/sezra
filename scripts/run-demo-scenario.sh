#!/usr/bin/env bash

set -e

REQUIRED_SERVICES=(
  "sezra-rabbitmq"
  "sezra-postgres"
  "sezra-qdrant"
  "sezra-event-store-service"
  "sezra-embedding-service"
  "sezra-analyzer-service"
  "sezra-api-service"
  "sezra-spike-detector-service"
)

echo "Checking SEZRA runtime..."

for service in "${REQUIRED_SERVICES[@]}"; do
  if ! docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
    echo "Runtime not ready. Starting SEZRA services..."
    ./scripts/init-demo-runtime.sh
    break
  fi
done

echo "Resetting demo data..."
./scripts/reset-demo-data.sh >/dev/null 2>&1

echo "Ensuring spike detector is running..."
docker compose up -d spike-detector-service >/dev/null 2>&1
echo "Running metric-to-metric demo scenario..."
./scripts/demo-metric-context.sh --quiet

echo "Waiting for analysis..."

for attempt in {1..10}; do
  analysis="$(curl -s http://localhost:8000/analyses/latest | jq -c '.payload.human_readable // null')"

  if [ "$analysis" != "null" ]; then
    echo
    echo "Latest SEZRA analysis:"
    echo
    echo "$analysis" | jq
    exit 0
  fi

  sleep 1
done

echo "No analysis generated."
exit 1