#!/usr/bin/env bash
set -euo pipefail

docker compose --profile enrichment run --rm \
  --workdir /app \
  level-1-enricher-service \
  sh -c "
    pip install pytest >/dev/null &&
    PYTHONPATH=/app python -m pytest -q /app/tests
  "