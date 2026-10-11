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

# 5) Ruff check and format
echo "5) Checking ruff in backend..."
cd "$REPO_ROOT/backend"
uv run ruff check .
uv run ruff format --check .
cd "$REPO_ROOT"
echo "PASS: Ruff clean."

# 6) Hygiene check
echo "6) Running hygiene check..."
./scripts/check_hygiene.sh
echo "PASS: Hygiene check passed."

echo "PASS: All T-09b acceptance checks passed."
