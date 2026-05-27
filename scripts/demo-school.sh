#!/bin/bash

set -e

echo "Creating school context email..."

cat > data/json-inbox/email-context.json <<'EOF'
{
  "source_type": "context",
  "context_type": "email",
  "sender": "principal@school.org",
  "subject": "New school schedule",
  "text": "Starting next Monday, school begins at 7:30 AM instead of 8:00 AM."
}
EOF

docker compose up --build json-file-adapter

echo "Creating grade baseline..."

cat > data/json-inbox/grade-baseline.json <<'EOF'
{
  "source_type": "observation",
  "metric": "math_test_average",
  "grade_level": 8,
  "value": 78
}
EOF

docker compose up --build json-file-adapter

echo "Creating grade drop..."

cat > data/json-inbox/grade-drop.json <<'EOF'
{
  "source_type": "observation",
  "metric": "math_test_average",
  "grade_level": 8,
  "value": 62
}
EOF

docker compose up --build json-file-adapter

echo "Demo events published."
echo "Check logs with:"
echo "docker compose logs --tail=50 drop-detector-service"
echo "docker compose logs --tail=50 analyzer-service"
echo "docker compose logs --tail=50 event-store-service"