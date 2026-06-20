#!/usr/bin/env bash
set -euo pipefail

API_URL="${SEZRA_API_URL:-http://localhost:8000}"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <event-id>"
  exit 1
fi

event_id="$1"
timeline_json="$(curl -s "$API_URL/events/timeline/$event_id")"

echo
echo "SEZRA Timeline"
echo "=============="
echo

echo "$timeline_json" | jq -r '
.[] |
"["
+ .received_at
+ "]\n"
+ .event_type
+ "\nEvent ID: "
+ .event_id
+ "\nSource  : "
+ .source
+ "\n"
'