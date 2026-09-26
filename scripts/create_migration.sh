#!/bin/bash
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: ./scripts/create_migration.sh 'migration message'"
  exit 1
fi

MESSAGE="$1"

echo "Creating migration: $MESSAGE"
uv run alembic revision --autogenerate -m "$MESSAGE"
echo "Migration created. Review before applying."
