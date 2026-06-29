#!/usr/bin/env bash
set -euo pipefail

docker compose run --rm \
  --workdir /app \
  -v "$(pwd)/services/benchmark-service:/app" \
  python-service-base \
  sh -c "
    pip install pytest >/dev/null &&
    PYTHONPATH=/app python -m pytest -q /app/tests
  "