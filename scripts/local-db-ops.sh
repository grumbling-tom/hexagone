#!/bin/sh
# Run database operations against the local Postgres, via the one-shot
# `migrate` compose service (same image/env as the backend).
# Usage:
#   ./scripts/local-db-ops.sh migrate   — apply pending migrations
#   ./scripts/local-db-ops.sh reset      — drop all tables and reapply migrations

set -e

action="${1:?Usage: $0 <migrate|reset>}"

case "$action" in
  migrate)
    # Default command of the migrate service is `alembic upgrade head`.
    docker compose run --rm migrate
    ;;
  reset)
    # Reuse the existing reset logic (drop all tables + alembic_version, then
    # re-migrate) from the db handler so the destructive path stays in one place.
    docker compose run --rm --entrypoint python migrate -c \
      "from src.app.handlers.db import reset_database, run_migrations; reset_database(); run_migrations()"
    ;;
  *)
    echo "Unknown action: $action"
    echo "Usage: $0 <migrate|reset>"
    exit 1
    ;;
esac
