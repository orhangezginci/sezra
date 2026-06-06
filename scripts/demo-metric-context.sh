#!/usr/bin/env bash

set -e

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
  "value": 94
}
EOF

log "Creating API latency observations..."

cat > "$INBOX/api-latency-baseline-1.json" <<EOF
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 178
}
EOF

cat > "$INBOX/api-latency-baseline-2.json" <<EOF
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 181
}
EOF

cat > "$INBOX/api-latency-baseline-3.json" <<EOF
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 184
}
EOF

cat > "$INBOX/api-latency-spike.json" <<EOF
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 420
}
EOF

log "Publishing demo events..."

if [ "$QUIET" = true ]; then
  docker compose up --no-build --force-recreate json-file-adapter >/dev/null 2>&1
else
  docker compose up --no-build --force-recreate json-file-adapter
fi

log "Metric-to-metric demo events published."