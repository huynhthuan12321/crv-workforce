#!/usr/bin/env bash
set -euo pipefail

ensure_db() {
  local name="$1"
  local user="${DB__USER:-default}"
  local exists
  exists="$(docker compose exec -T db psql -U "$user" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$name'" | tr -d '[:space:]')"
  if [[ "$exists" != "1" ]]; then
    docker compose exec -T db createdb -U "$user" "$name"
  fi
}

count_matches() {
  local text="$1"
  local pattern="$2"
  if [[ "$text" =~ $pattern ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    echo "0"
  fi
}

run_capture() {
  local name="$1"
  shift
  echo
  echo "== $name =="
  local output
  output="$("$@" 2>&1)"
  echo "$output"
  printf '%s' "$output"
}

docker compose up -d db redis
ensure_db "crv_workforce_test"
ensure_db "crv_workforce_migcheck"

export APP__ENV="${APP__ENV:-development}"
export DB__HOST="localhost"
export DB__PORT="${DB__PORT:-5432}"
export DB__USER="${DB__USER:-default}"
export DB__PASSWORD="${DB__PASSWORD:-password}"
export REDIS__HOST="localhost"
export REDIS__PASSWORD="${REDIS__PASSWORD:-password}"
export CRV_REQUIRE_POSTGRES=1
export TEST_DATABASE_URL="postgresql+asyncpg://${DB__USER}:${DB__PASSWORD}@localhost:5432/crv_workforce_test"

pytest_output="$(run_capture pytest python -m pytest -q)"
pytest_passed="$(count_matches "$pytest_output" '([0-9]+)[[:space:]]+passed')"
pytest_skipped="$(count_matches "$pytest_output" '([0-9]+)[[:space:]]+skipped')"
if [[ "$pytest_skipped" != "0" ]]; then
  echo "PostgreSQL-required pytest run must have 0 skipped tests, got $pytest_skipped" >&2
  exit 1
fi

export DB__NAME="crv_workforce_migcheck"
run_capture "alembic migration check" bash -lc "alembic upgrade head && alembic downgrade 0002 && alembic upgrade head && alembic check" >/dev/null

pushd webapp >/dev/null
run_capture "npm test" npm test >/dev/null
run_capture "npm run build" npm run build >/dev/null
run_capture "npm run test:overflow" npm run test:overflow >/dev/null
popd >/dev/null

echo
echo "| Group | Passed | Skipped | Status |"
echo "|---|---:|---:|---|"
echo "| pytest | $pytest_passed | $pytest_skipped | OK |"
echo "| alembic | n/a | n/a | OK |"
echo "| npm test | n/a | n/a | OK |"
echo "| npm build | n/a | n/a | OK |"
echo "| overflow 360/390/430 | n/a | n/a | OK |"
