#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INBOX="$PROJECT_ROOT/data/json-inbox"

mkdir -p "$INBOX"
cd "$PROJECT_ROOT"

echo "Creating Jenkins deployment context..."

cat > "$INBOX/jenkins-deployment-context.json" <<'EOF'
{
  "source_type": "context",
  "context_type": "jenkins",
  "job": "checkout-api-deploy",
  "build_number": 184,
  "text": "Jenkins deployed checkout-api version 1.12.0 with new request logging middleware."
}
EOF

docker compose up --build json-file-adapter

echo "Creating API latency baseline..."

cat > "$INBOX/api-latency-baseline.json" <<'EOF'
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 180
}
EOF

docker compose up --build json-file-adapter

echo "Creating API latency spike..."

cat > "$INBOX/api-latency-spike.json" <<'EOF'
{
  "source_type": "observation",
  "metric": "api_latency_ms",
  "service": "checkout-api",
  "value": 420
}
EOF

docker compose up --build json-file-adapter

echo "DevOps demo events published."
echo "Check logs with:"
echo "docker compose logs --tail=50 drop-detector-service"
echo "docker compose logs --tail=50 analyzer-service"
echo "docker compose logs --tail=50 event-store-service"