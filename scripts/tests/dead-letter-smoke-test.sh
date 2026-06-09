#!/usr/bin/env bash

set -e
echo "Ensuring SEZRA runtime is running..."
./scripts/init-demo-runtime.sh >/dev/null 2>&1
echo "Running SEZRA dead-letter smoke test..."

echo "Publishing invalid event..."

docker compose exec -T rabbitmq sh -lc '
rabbitmqadmin \
  -u "$RABBITMQ_DEFAULT_USER" \
  -p "$RABBITMQ_DEFAULT_PASS" \
  publish \
  exchange=sezra.stream.anomaly \
  routing_key="" \
  payload="this is not valid json"
' >/dev/null

echo "Waiting for dead-letter persistence..."
sleep 3

response="$(curl -s http://localhost:8000/events/type/EventProcessingFailed)"

if [[ "$response" != *"EventProcessingFailed"* ]]; then
  echo "Dead-letter event was not persisted:"
  echo "$response"
  exit 1
fi

echo "SEZRA dead-letter smoke test passed."
