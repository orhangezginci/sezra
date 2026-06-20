#!/usr/bin/env bash
set -euo pipefail

API_URL="${SEZRA_API_URL:-http://localhost:8000}"

event_json="$(curl -s "$API_URL/investigations/latest")"

echo
echo "SEZRA Investigation"
echo "==================="
echo

echo "$event_json" | jq -r '.payload.summary'

echo
echo "Metadata"
echo "--------"
echo "$event_json" | jq -r '"Event ID: " + .event_id'
echo "$event_json" | jq -r '"Occurred: " + .occurred_at'
echo "$event_json" | jq -r '"Correlation ID: " + .correlation_id'