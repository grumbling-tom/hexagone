#!/bin/sh
# Invoke the db-ops Lambda container locally.
# Usage:
#   ./scripts/db-ops.sh migrate   — apply pending migrations
#   ./scripts/db-ops.sh reset     — drop all tables and reapply migrations

set -e

LAMBDA_URL="http://localhost:9001/2015-03-31/functions/function/invocations"

action="${1:?Usage: $0 <migrate|reset>}"

case "$action" in
  migrate|reset) ;;
  *)
    echo "Unknown action: $action"
    echo "Usage: $0 <migrate|reset>"
    exit 1
    ;;
esac

echo "Invoking db-ops: $action..."

response=$(curl -s -X POST \
  "$LAMBDA_URL" \
  -H "Content-Type: application/json" \
  -d "{\"action\": \"$action\"}")

if [ $? -ne 0 ]; then
  echo "Failed to invoke db-ops Lambda"
  exit 1
fi

echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
