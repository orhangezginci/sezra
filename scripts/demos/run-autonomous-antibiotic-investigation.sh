#!/usr/bin/env bash
set -euo pipefail

API_URL="${SEZRA_API_URL:-http://localhost:8000}"

echo "SEZRA Autonomous Antibiotic Investigation Demo"
echo

echo "1) Starting SEZRA core services..."
docker compose --profile legacy-detectors up -d

publish_raw() {
  docker compose exec -T rabbitmq sh -lc "
rabbitmqadmin \
  -u \"\$RABBITMQ_DEFAULT_USER\" \
  -p \"\$RABBITMQ_DEFAULT_PASS\" \
  publish \
  exchange=sezra.stream.raw \
  routing_key=\"\" \
  payload='$1'
"
}

echo
echo "2) Publishing supplier transition context..."

publish_raw '{"event_id":"aaaa1111-1111-1111-1111-111111111111","event_type":"GmailMessageReceived","source":"demo-script","occurred_at":"2026-06-22T15:00:00Z","correlation_id":null,"causation_id":null,"payload":{"from":"pharmacy@example.com","subject":"Supplier transition","text":"Supplier transition for Amoxicillin IV starts tonight."}}'

echo
echo "3) Publishing antibiotic delivery delay measurement..."

publish_raw '{"event_id":"bbbb2222-2222-2222-2222-222222222222","event_type":"JsonFileReceived","source":"demo-script","occurred_at":"2026-06-22T15:01:00Z","correlation_id":null,"causation_id":null,"payload":{"metric":"antibiotic_delivery_delay_minutes","service":"ward-medication-workflow","value":52,"baseline":8,"labels":{"medication":"amoxicillin_iv","department":"ward"}}}'

echo
echo "4) Waiting for detector/analyzer pipeline..."
sleep 15

echo
echo "5) Latest analysis events:"
curl -s "$API_URL/events/type/AnalysisGenerated" \
  | jq '.[-3:] | map({event_id, occurred_at, summary: .payload.summary, related_contexts: .payload.related_contexts})'

echo
echo "6) Latest investigation:"
curl -s "$API_URL/investigations/latest" \
  | jq '{event_id, occurred_at, subject: .payload.subject, evidence: [.payload.evidence[]? | {type: .evidence_type, source, text}]}'

echo
echo "Demo run complete."