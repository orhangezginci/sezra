#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INBOX="$PROJECT_ROOT/data/json-inbox"

mkdir -p "$INBOX"
cd "$PROJECT_ROOT"

publish_json_file() {
  local filename="$1"
  local content="$2"

  echo "$content" > "$INBOX/$filename"

  docker compose up --build json-file-adapter
}

echo "Creating CPU usage metric context..."

publish_json_file "cpu-usage-context.json" '{
  "source_type": "context",
  "context_type": "metric",
  "metric": "cpu_usage_percent",
  "service": "checkout-api",
  "value": 94
}'

echo "Creating API latency observations..."

values=(180 185 178 420)

for index in "${!values[@]}"; do
  value="${values[$index]}"

  if [ "$value" -eq 420 ]; then
    filename="api-latency-spike.json"
  else
    filename="api-latency-baseline-$((index + 1)).json"
  fi

  publish_json_file "$filename" "{
  \"source_type\": \"observation\",
  \"metric\": \"api_latency_ms\",
  \"service\": \"checkout-api\",
  \"value\": $value
}"
done

echo "Metric-to-metric demo events published."
echo "Check logs with:"
echo "docker compose logs --tail=80 spike-detector-service"
echo "docker compose logs --tail=80 analyzer-service"
echo "docker compose logs --tail=80 event-store-service"