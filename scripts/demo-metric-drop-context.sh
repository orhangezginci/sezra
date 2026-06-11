#!/usr/bin/env bash

set -e

docker compose --profile deviation-detectors restart \
  deviation-detector-service >/dev/null 2>&1 || true

sleep 3

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INBOX="$PROJECT_ROOT/data/json-inbox"

QUIET=false

if [ "${1:-}" = "--quiet" ]; then
  QUIET=true
fi

log() {
  if [ "$QUIET" = false ]; then
    echo "$1"
  fi
}

mkdir -p "$INBOX"

log "Creating CPU usage metric context..."

cat > "$INBOX/cpu-usage-context.json" <<EOF
{
  "source_type": "context",
  "context_type": "metric",
  "metric": "cpu_usage_percent",
  "service": "checkout-api",
  "value": 18
}
EOF

log "Creating API latency drop observations..."

cat > "$INBOX/api-latency-baseline-1.json" <<EOF
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 420
}
EOF

cat > "$INBOX/api-latency-baseline-2.json" <<EOF
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 418
}
EOF

cat > "$INBOX/api-latency-baseline-3.json" <<EOF
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 421
}
EOF

cat > "$INBOX/api-latency-drop.json" <<EOF
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 180
}
EOF

log "Publishing demo events..."

if [ "$QUIET" = true ]; then
  docker compose up --no-build --force-recreate json-file-adapter >/dev/null 2>&1
else
  docker compose up --no-build --force-recreate json-file-adapter
fi

log "Metric drop demo events published."