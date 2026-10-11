#!/usr/bin/env bash
# scripts/accept/T-09b.sh
# Acceptance test script for T-09b: LLM calls fixes, test DB isolation, and latency tracking
set -euo pipefail

echo "Running acceptance script for T-09b..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# 1) Check files exist
echo "1) Checking required files exist..."
test -f backend/tests/conftest.py || { echo "FAIL: backend/tests/conftest.py missing"; exit 1; }
test -f backend/app/llm/gateway.py || { echo "FAIL: backend/app/llm/gateway.py missing"; exit 1; }
test -f backend/tests/test_gateway.py || { echo "FAIL: backend/tests/test_gateway.py missing"; exit 1; }
echo "PASS: Required files exist."

# 2) Check kharcha_dev llm_calls count before and after full backend pytest run
echo "2) Checking kharcha_dev isolation during full backend test suite..."
cd "$REPO_ROOT/backend"
DEV_COUNT_BEFORE=$(uv run --env-file ../.env.dev python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
async def count_rows():
    async with AsyncSessionLocal() as s:
        print((await s.execute(text('SELECT count(*) FROM llm_calls'))).scalar())
asyncio.run(count_rows())
")

# Run full backend pytest
uv run --env-file ../.env.dev pytest -q

DEV_COUNT_AFTER=$(uv run --env-file ../.env.dev python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
async def count_rows():
    async with AsyncSessionLocal() as s:
        print((await s.execute(text('SELECT count(*) FROM llm_calls'))).scalar())
asyncio.run(count_rows())
")

if [ "$DEV_COUNT_BEFORE" != "$DEV_COUNT_AFTER" ]; then
    echo "FAIL: kharcha_dev llm_calls count changed during tests! Before: $DEV_COUNT_BEFORE, After: $DEV_COUNT_AFTER"
    exit 1
fi
echo "PASS: kharcha_dev untouched during tests (count unchanged at $DEV_COUNT_BEFORE)."

# 3) Run full backend pytest twice
echo "3) Running full backend pytest suite twice..."
uv run --env-file ../.env.dev pytest -q
uv run --env-file ../.env.dev pytest -q
echo "PASS: Backend pytest suite passed twice."

# 4) Run scripts/accept/T-09.sh to ensure earlier acceptance checks still pass
echo "4) Verifying scripts/accept/T-09.sh still passes..."
cd "$REPO_ROOT"
./scripts/accept/T-09.sh
echo "PASS: scripts/accept/T-09.sh passed."

# 5) Live uvicorn healthz checks (4 overridden dependency runs + 1 normal run)
echo "5) Running live uvicorn healthz dependency checks..."
APP_PORT=8004
UNUSED_PORT=59999

run_and_check_healthz() {
  local desc="$1"
  local env_override="$2"
  local exp_db="$3"
  local exp_redis="$4"
  local exp_llm="$5"
  local exp_erp="$6"

  echo "  -> Testing $desc..."
  # Start uvicorn in background with specific env override
  cd "$REPO_ROOT/backend"
  # shellcheck disable=SC2086
  env $env_override uv run --env-file ../.env.dev uvicorn app.main:app --port "$APP_PORT" --host 127.0.0.1 > /dev/null 2>&1 &
  local app_pid=$!

  # Wait for uvicorn to respond
  local ready=0
  for _ in {1..20}; do
    if curl -s -m 2 "http://127.0.0.1:$APP_PORT/v1/healthz" > /dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 0.2
  done

  if [ "$ready" -ne 1 ]; then
    kill "$app_pid" 2>/dev/null || true
    wait "$app_pid" 2>/dev/null || true
    echo "FAIL: uvicorn failed to start or respond on port $APP_PORT for $desc"
    exit 1
  fi

  local resp
  resp=$(curl -s -m 5 "http://127.0.0.1:$APP_PORT/v1/healthz")
  echo "     Response: $resp"

  # Kill uvicorn and ensure it is stopped
  kill "$app_pid" 2>/dev/null || true
  wait "$app_pid" 2>/dev/null || true
  sleep 0.2

  local act_db act_redis act_llm act_erp
  act_db=$(echo "$resp" | jq -r '.db')
  act_redis=$(echo "$resp" | jq -r '.redis')
  act_llm=$(echo "$resp" | jq -r '.llm')
  act_erp=$(echo "$resp" | jq -r '.erp')

  if [ "$act_db" != "$exp_db" ] || [ "$act_redis" != "$exp_redis" ] || [ "$act_llm" != "$exp_llm" ] || [ "$act_erp" != "$exp_erp" ]; then
    echo "FAIL: Expected db=$exp_db, redis=$exp_redis, llm=$exp_llm, erp=$exp_erp; got db=$act_db, redis=$act_redis, llm=$act_llm, erp=$act_erp"
    exit 1
  fi
}

# Run 1: LITELLM_URL unreachable -> llm degraded, others ok
run_and_check_healthz "LITELLM_URL unreachable" "LITELLM_URL=http://127.0.0.1:$UNUSED_PORT" "ok" "ok" "degraded" "ok"

# Run 2: REDIS_URL unreachable -> redis down, others ok
run_and_check_healthz "REDIS_URL unreachable" "REDIS_URL=redis://127.0.0.1:$UNUSED_PORT/0" "ok" "down" "ok" "ok"

# Run 3: ERP_BASE_URL unreachable -> erp down, others ok
run_and_check_healthz "ERP_BASE_URL unreachable" "ERP_BASE_URL=http://127.0.0.1:$UNUSED_PORT" "ok" "ok" "ok" "down"

# Run 4: DATABASE_URL unreachable -> db down, others ok
DEV_DB_URL=$(grep '^DATABASE_URL=' "$REPO_ROOT/.env.dev" | cut -d= -f2-)
BAD_DB_URL=$(echo "$DEV_DB_URL" | sed "s/:5432\//:$UNUSED_PORT\//")
run_and_check_healthz "DATABASE_URL unreachable" "DATABASE_URL=$BAD_DB_URL" "down" "ok" "ok" "ok"

# Run 5: Nothing overridden -> all four ok
run_and_check_healthz "All services healthy" "" "ok" "ok" "ok" "ok"

echo "PASS: Live uvicorn healthz checks passed."

# 6) Ruff check and format
echo "6) Checking ruff in backend..."
cd "$REPO_ROOT/backend"
uv run ruff check .
uv run ruff format --check .
cd "$REPO_ROOT"
echo "PASS: Ruff clean."

# 7) Hygiene check
echo "7) Running hygiene check..."
./scripts/check_hygiene.sh
echo "PASS: Hygiene check passed."

echo "PASS: All T-09b acceptance checks passed."

