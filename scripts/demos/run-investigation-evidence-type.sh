#!/usr/bin/env bash
set -euo pipefail

API_URL="${SEZRA_API_URL:-http://localhost:8000}"

echo "SEZRA Investigation Evidence Type Demo"
echo

echo "1) Starting SEZRA core services..."
docker compose up -d

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

publish_investigation() {
  docker compose exec -T rabbitmq sh -lc "
rabbitmqadmin \
  -u \"\$RABBITMQ_DEFAULT_USER\" \
  -p \"\$RABBITMQ_DEFAULT_PASS\" \
  publish \
  exchange=sezra.stream.investigation \
  routing_key=\"\" \
  payload='$1'
"
}

echo
echo "2) Publishing evidence events..."

publish_raw '{"event_id":"11111111-1111-1111-1111-111111111111","event_type":"GmailMessageReceived","source":"demo-script","occurred_at":"2026-06-22T15:00:00Z","correlation_id":null,"causation_id":null,"payload":{"from":"pharmacy@example.com","subject":"Supplier change","text":"Supplier transition may cause antibiotic delivery delays."}}'

publish_raw '{"event_id":"22222222-2222-2222-2222-222222222222","event_type":"JsonFileReceived","source":"demo-script","occurred_at":"2026-06-22T15:01:00Z","correlation_id":null,"causation_id":null,"payload":{"metric":"antibiotic_restock_delay_minutes","service":"pharmacy-inventory","value":47,"baseline":8,"labels":{"medication":"amoxicillin_iv","department":"pharmacy"}}}'

publish_raw '{"event_id":"33333333-3333-3333-3333-333333333333","event_type":"GmailMessageReceived","source":"demo-script","occurred_at":"2026-06-22T15:02:00Z","correlation_id":null,"causation_id":null,"payload":{"from":"family@example.com","subject":"Dose delayed","text":"Patient family reports that an antibiotic dose was delayed again."}}'

echo
echo "3) Waiting for evidence events to be embedded..."
sleep 10

echo
echo "4) Publishing investigation request..."

publish_investigation '{"event_id":"88888888-8888-8888-8888-888888888888","event_type":"InvestigationRequested","source":"demo-script","occurred_at":"2026-06-22T15:03:00Z","correlation_id":"88888888-8888-8888-8888-888888888888","causation_id":null,"payload":{"reason":"human_reported_issue","subject":"antibiotic dose delayed","summary":"Patient family reports that an antibiotic dose was delayed again."}}'

echo
echo "5) Waiting for investigation..."
sleep 10

echo
echo "6) Latest investigation evidence types:"
curl -s "$API_URL/investigations/latest" \
  | jq '.payload.evidence[] | {type: .evidence_type, source, text}'

echo
echo "Demo run complete."