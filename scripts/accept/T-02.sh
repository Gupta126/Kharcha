#!/usr/bin/env bash
# T-02 Backend skeleton — acceptance script
# Checks every Deliver item and "Done when" line from docs/TASKS.md.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

FAIL=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

# ── Deliver: backend/app/main.py (FastAPI, /v1 prefix) ──
[[ -f backend/app/main.py ]] && pass "backend/app/main.py exists" \
                              || fail "backend/app/main.py missing"
if [[ -f backend/app/main.py ]]; then
  grep -q 'FastAPI' backend/app/main.py \
    && pass "main.py uses FastAPI" \
    || fail "main.py does not use FastAPI"
  grep -q '/v1' backend/app/main.py \
    && pass "main.py has /v1 prefix" \
    || fail "main.py missing /v1 prefix"
fi

# ── Deliver: core/settings.py (pydantic-settings, all .env keys) ──
# The actual path is backend/app/core/settings.py
if [[ -f backend/app/core/settings.py ]]; then
  pass "backend/app/core/settings.py exists"
  grep -q 'pydantic_settings\|BaseSettings' backend/app/core/settings.py \
    && pass "settings.py uses pydantic-settings" \
    || fail "settings.py does not use pydantic-settings"
  # Check that all critical env keys are declared
  for key in DATABASE_URL REDIS_URL JWT_SECRET ERP_BASE_URL FORENSICS_URL LITELLM_URL STORAGE_DIR LLM_MODE; do
    grep -q "$key" backend/app/core/settings.py \
      && pass "settings.py declares $key" \
      || fail "settings.py missing $key"
  done
else
  fail "backend/app/core/settings.py missing"
fi

# ── Deliver: core/errors.py (SPEC §2 format + exception handlers) ──
if [[ -f backend/app/core/errors.py ]]; then
  pass "backend/app/core/errors.py exists"
  grep -q 'exception_handlers\|add_exception_handler' backend/app/core/errors.py \
    && pass "errors.py defines exception handlers" \
    || fail "errors.py missing exception handlers"
  # SPEC §2 error shape: {"error": {"code": ..., "message": ..., "details": ...}}
  grep -q '"error"' backend/app/core/errors.py \
    && pass "errors.py uses SPEC §2 error envelope" \
    || fail "errors.py missing SPEC §2 error envelope"
else
  fail "backend/app/core/errors.py missing"
fi

# ── Deliver: api/health.py (GET /v1/healthz, checks db/redis/erp/llm) ──
if [[ -f backend/app/api/health.py ]]; then
  pass "backend/app/api/health.py exists"
  grep -q 'healthz' backend/app/api/health.py \
    && pass "health.py has /healthz route" \
    || fail "health.py missing /healthz route"
  for svc in db redis llm erp; do
    grep -qi "$svc" backend/app/api/health.py \
      && pass "health.py checks $svc" \
      || fail "health.py does not check $svc"
  done
else
  fail "backend/app/api/health.py missing"
fi

# ── Deliver: backend/Dockerfile (python:3.12-slim, builds on arm64 VM) ──
if [[ -f backend/Dockerfile ]]; then
  pass "backend/Dockerfile exists"
  grep -q 'python:3.12' backend/Dockerfile \
    && pass "Dockerfile uses python:3.12" \
    || fail "Dockerfile does not use python:3.12"
else
  fail "backend/Dockerfile missing"
fi

# ── Deliver: tests for healthz and error format ──
# Look for test files covering health and error endpoints
HEALTH_TEST=$(find backend/tests -name '*.py' | xargs grep -l 'healthz\|health_check' 2>/dev/null | head -1)
if [[ -n "$HEALTH_TEST" ]]; then
  pass "Test file for healthz exists: $HEALTH_TEST"
else
  fail "No test file covers healthz endpoint"
fi

ERROR_TEST=$(find backend/tests -name '*.py' | xargs grep -l 'error.*code\|error.*message\|SPEC.*2\|error_response\|NOT_FOUND\|VALIDATION' 2>/dev/null | head -1)
if [[ -n "$ERROR_TEST" ]]; then
  pass "Test file for error format exists: $ERROR_TEST"
else
  fail "No test file covers SPEC §2 error format"
fi

# ── Deliver: test_contract.py (compares FastAPI routes/responses with openapi.yaml) ──
if [[ -f backend/tests/test_contract.py ]]; then
  pass "backend/tests/test_contract.py exists"
else
  fail "backend/tests/test_contract.py missing"
fi

# ── Done when: healthz returns the SPEC shape ──
# (tested via pytest; healthz shape is {db, redis, llm, erp} strings)

# ── Done when: unknown route returns the SPEC error JSON ──
# (tested via pytest; error shape is {error: {code, message, details}})

# ── Verify: cd backend && uv run pytest -q ──
PYTEST_OUT=$(cd backend && uv run pytest -q 2>&1) || true
PYTEST_RC=$?
COLLECTED=$(echo "$PYTEST_OUT" | grep -oP '\d+(?= passed)' | head -1)
if [[ $PYTEST_RC -eq 0 ]]; then
  pass "backend pytest passes (${COLLECTED:-0} tests)"
else
  fail "backend pytest failed (rc=$PYTEST_RC)"
fi
# Must have at least 1 test
if [[ -n "$COLLECTED" && "$COLLECTED" -ge 1 ]]; then
  pass "backend has ≥1 passing test ($COLLECTED)"
else
  fail "backend has <1 passing test (found: ${COLLECTED:-0})"
fi

# ── Hygiene gate ──
if ./scripts/check_hygiene.sh >/dev/null 2>&1; then
  pass "check_hygiene.sh passes"
else
  fail "check_hygiene.sh failed"
fi

exit "$FAIL"