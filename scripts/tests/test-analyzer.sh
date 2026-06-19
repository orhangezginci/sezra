set -euo pipefail

docker compose run --rm analyzer-service sh -lc \
  'PYTHONPATH=/app pytest tests/test_analyzer.py -v'