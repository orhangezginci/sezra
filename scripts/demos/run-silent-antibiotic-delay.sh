#!/usr/bin/env bash
set -euo pipefail

echo "SEZRA Silent Antibiotic Delay Demo"
echo

echo "1) Starting SEZRA core services..."
docker compose up -d --build

echo
echo "2) Stopping Gmail adapter for deterministic demo run..."
docker compose stop gmail-adapter-service >/dev/null 2>&1 || true

echo
echo "3) Publishing demo events..."

publish() {
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

publish '{"event_id":"11111111-1111-1111-1111-111111111111","event_type":"GmailMessageReceived","source":"demo-script","occurred_at":"2026-06-17T07:00:00Z","correlation_id":null,"causation_id":null,"payload":{"from":"pharmacy-operations@medisezra.example","subject":"SEZRA Pharmacy: New antibiotic supplier starts tonight","text":"Pharmacy operations update: Starting tonight, we are switching to a new supplier for Amoxicillin IV. The transition should not affect patient care. Initial deliveries may show slight timing variations during the first 24 hours."}}'

publish '{"event_id":"22222222-2222-2222-2222-222222222222","event_type":"JsonFileReceived","source":"demo-script","occurred_at":"2026-06-17T08:00:00Z","correlation_id":null,"causation_id":null,"payload":{"source_type":"metric","metric":"antibiotic_restock_delay_minutes","service":"pharmacy-inventory","value":47,"baseline":8,"labels":{"medication":"amoxicillin_iv","department":"pharmacy"}}}'

publish '{"event_id":"33333333-3333-3333-3333-333333333333","event_type":"JsonFileReceived","source":"demo-script","occurred_at":"2026-06-17T09:00:00Z","correlation_id":null,"causation_id":null,"payload":{"source_type":"metric","metric":"medication_administration_delay_minutes","service":"ward-medication-workflow","value":68,"baseline":19,"labels":{"medication":"amoxicillin_iv","patient_group":"high_risk"}}}'

publish '{"event_id":"44444444-4444-4444-4444-444444444444","event_type":"GmailMessageReceived","source":"demo-script","occurred_at":"2026-06-17T09:30:00Z","correlation_id":null,"causation_id":null,"payload":{"from":"family.member@example.com","subject":"SEZRA Concern: Antibiotic dose delayed again","text":"Patient family report: My father was supposed to receive his antibiotic dose hours ago. This is the second delay this week. He is already weak and we are worried his infection is getting worse."}}'

echo
echo "4) Waiting for services to process events..."
sleep 10

show_events() {
  local title="$1"
  local event_type="$2"
  local jq_filter="$3"

  echo
  echo "$title"
  curl --max-time 5 -s "http://localhost:8000/events/type/$event_type" \
    | jq "$jq_filter" || true
}

show_events "5) Latest GmailMessageReceived events:" "GmailMessageReceived" '.[-3:]'
show_events "6) Latest JsonFileReceived events:" "JsonFileReceived" '.[-3:]'
show_events "7) Latest AnomalyDetected events:" "AnomalyDetected" '.[-5:]'
show_events "8) Latest AnalysisGenerated events:" "AnalysisGenerated" '.[-5:]'
show_events "8) Latest InvestigationGenerated events:" "InvestigationGenerated" '.[-3:]'

echo
echo "Demo run complete."