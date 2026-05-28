#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

INBOX="$PROJECT_ROOT/data/json-inbox"
PROCESSED="$PROJECT_ROOT/data/json-processed"

echo "Cleaning inbox..."
rm -f "$INBOX"/*.json || true

echo "Cleaning processed..."
rm -f "$PROCESSED"/*.json || true

echo "Clearing PostgreSQL event store..."

docker exec -i sezra-postgres psql -U sezra -d sezra <<EOF
TRUNCATE TABLE event_envelopes RESTART IDENTITY;
EOF

echo "Recreating Qdrant collection..."

curl -X DELETE "http://localhost:6333/collections/sezra_events" >/dev/null 2>&1 || true

curl -X PUT "http://localhost:6333/collections/sezra_events" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'

echo
echo "SEZRA demo data reset complete."