#!/usr/bin/env bash
set -euo pipefail

API_URL="${SEZRA_API_URL:-http://localhost:8000}"

event_json="$(curl -s "$API_URL/investigations/latest")"

echo
echo "SEZRA Investigation"
echo "==================="
echo

echo "Subject"
echo "-------"
echo "$event_json" | jq -r '.payload.subject'

echo
echo "Evidence"
echo "--------"

echo "$event_json" | jq -r '
.payload.evidence
| to_entries[]
| "\n[\(.value.evidence_type // "unknown" | ascii_upcase)] \(.value.text)\n    Source: \(.value.source)\n    Score : \((.value.score * 1000 | round) / 1000)"
'

echo
echo "Metadata"
echo "--------"
echo "$event_json" | jq -r '"Event ID       : " + .event_id'
echo "$event_json" | jq -r '"Correlation ID: " + .correlation_id'
echo "$event_json" | jq -r '"Occurred       : " + .occurred_at'