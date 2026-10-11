#!/usr/bin/env bash
# scripts/accept/T-09.sh
# Acceptance test script for T-09: LLM gateway client and stub mode
set -euo pipefail

echo "Running acceptance script for T-09..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# 1) Check files exist
echo "1) Checking required deliver files exist..."
test -f backend/app/llm/gateway.py || { echo "FAIL: backend/app/llm/gateway.py missing"; exit 1; }
test -f backend/app/llm/prompts/extract_text_v1.md || { echo "FAIL: backend/app/llm/prompts/extract_text_v1.md missing"; exit 1; }
test -f contracts/prompts/extract_text_v1.md || { echo "FAIL: contracts/prompts/extract_text_v1.md missing"; exit 1; }
test -d backend/tests/fixtures/llm/kh-extract-text || { echo "FAIL: fixtures/llm/kh-extract-text missing"; exit 1; }
test -d backend/tests/fixtures/llm/kh-extract-image || { echo "FAIL: fixtures/llm/kh-extract-image missing"; exit 1; }
test -d backend/tests/fixtures/llm/kh-agent || { echo "FAIL: fixtures/llm/kh-agent missing"; exit 1; }
test -d backend/tests/fixtures/llm/kh-parse || { echo "FAIL: fixtures/llm/kh-parse missing"; exit 1; }
test -f backend/tests/test_gateway.py || { echo "FAIL: backend/tests/test_gateway.py missing"; exit 1; }
echo "PASS: Deliver files exist."

# 2) Prompts single-source check
echo "2) Checking prompt single source integrity..."
cmp -s backend/app/llm/prompts/extract_text_v1.md contracts/prompts/extract_text_v1.md || {
    echo "FAIL: backend/app/llm/prompts/extract_text_v1.md does not match contracts/prompts/extract_text_v1.md";
    exit 1;
}
echo "PASS: Prompts match single source in contracts/."

# 3) Check that no vendor model names are hardcoded in backend/app/
echo "3) Checking no vendor model names in backend/app/..."
VENDOR_MATCHES=$(git grep -i -E "(llama|nemotron|mistral|qwen|gpt-4|claude-3)" backend/app/ || true)
if [ -n "$VENDOR_MATCHES" ]; then
    echo "FAIL: Found vendor model names in backend/app/:"
    echo "$VENDOR_MATCHES"
    exit 1
fi
echo "PASS: Zero vendor model names found in backend/app/."

# 4) Run pytest in backend for test_gateway.py and test_health.py
echo "4) Running pytest for gateway and health endpoints..."
cd "$REPO_ROOT/backend"
LLM_MODE=stub uv run --env-file ../.env.dev pytest -v tests/test_gateway.py tests/test_health.py

TEST_COUNT=$(LLM_MODE=stub uv run --env-file ../.env.dev pytest -q tests/test_gateway.py | tail -n 1 | awk '{print $1}')
echo "Gateway tests run summary: $TEST_COUNT"

# Verify llm_calls row has correct task from database
echo "4b) Checking that llm_calls row has correct task in database..."
TASK_CHECK=$(LLM_MODE=stub uv run --env-file ../.env.dev python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
async def check():
    async with AsyncSessionLocal() as s:
        res = await s.execute(text(\"SELECT task FROM llm_calls WHERE task IS NOT NULL ORDER BY created_at DESC LIMIT 1\"))
        print(res.scalar())
asyncio.run(check())
")
if [ -z "$TASK_CHECK" ] || [ "$TASK_CHECK" = "None" ]; then
    echo "FAIL: No llm_calls row found with non-null task"; exit 1;
fi
echo "PASS: Latest llm_calls row has task '$TASK_CHECK'."
cd "$REPO_ROOT"
echo "PASS: Gateway and health tests passed."

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

echo "PASS: All T-09 acceptance checks passed."
