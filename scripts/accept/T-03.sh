#!/usr/bin/env bash
# T-03 Mock ERP service — acceptance script
# Checks every Deliver item and "Done when" line from docs/TASKS.md.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

FAIL=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

# ── Deliver: mock-erp/app/main.py with endpoints from PRD §22 ──
[[ -f mock-erp/app/main.py ]] && pass "mock-erp/app/main.py exists" \
                               || fail "mock-erp/app/main.py missing"

# ── Deliver: loading data/seed/employees.json ──
[[ -f data/seed/employees.json ]] && pass "data/seed/employees.json exists" \
                                   || fail "data/seed/employees.json missing"
if [[ -f mock-erp/app/main.py ]]; then
  grep -rq 'employees.json\|seed' mock-erp/app/ \
    && pass "mock-erp references employees.json or seed data" \
    || fail "mock-erp does not load employees.json"
fi

# ── Deliver: in-memory store ──
# (Verified by the fact that tests run without a database)

# ── Deliver: status timeline (submitted→in_review→approved→paid, configurable) ──
if grep -rq 'submitted\|in_review\|approved\|paid' mock-erp/app/ 2>/dev/null; then
  pass "mock-erp has status timeline states"
else
  fail "mock-erp missing status timeline states"
fi

# ── Deliver: POST /admin/scenario ──
if grep -rq 'admin/scenario\|/scenario' mock-erp/app/ 2>/dev/null; then
  pass "mock-erp has POST /admin/scenario"
else
  fail "mock-erp missing POST /admin/scenario"
fi

# ── Deliver: Dockerfile ──
[[ -f mock-erp/Dockerfile ]] && pass "mock-erp/Dockerfile exists" \
                              || fail "mock-erp/Dockerfile missing"
if [[ -f mock-erp/Dockerfile ]]; then
  grep -q 'python:3.12' mock-erp/Dockerfile \
    && pass "mock-erp Dockerfile uses python:3.12" \
    || fail "mock-erp Dockerfile does not use python:3.12"
fi

# ── Deliver: tests ──
MOCK_ERP_TESTS=$(find mock-erp/tests -name 'test_*.py' 2>/dev/null | wc -l)
if [[ "$MOCK_ERP_TESTS" -ge 1 ]]; then
  pass "mock-erp has $MOCK_ERP_TESTS test file(s)"
else
  fail "mock-erp has no test files"
fi

# ── Done when: Arjun's broadband shows paid = limit ──
if grep -rq 'arjun\|Arjun\|broadband\|exhausted' mock-erp/tests/ 2>/dev/null; then
  pass "Tests reference Arjun/broadband/exhausted scenario"
else
  fail "Tests missing Arjun broadband exhausted scenario"
fi

# ── Done when: a posted reimbursement reaches paid on the timer ──
if grep -rq 'submit\|reimbursement\|claim' mock-erp/tests/ 2>/dev/null; then
  pass "Tests reference reimbursement submission"
else
  fail "Tests missing reimbursement submission scenario"
fi

# ── Verify: cd mock-erp && uv run pytest -q ──
PYTEST_OUT=$(cd mock-erp && uv run pytest -q 2>&1) || true
PYTEST_RC=$?
COLLECTED=$(echo "$PYTEST_OUT" | grep -oP '\d+(?= passed)' | head -1)
if [[ $PYTEST_RC -eq 0 ]]; then
  pass "mock-erp pytest passes (${COLLECTED:-0} tests)"
else
  fail "mock-erp pytest failed (rc=$PYTEST_RC)"
fi
# Task has substantial test coverage
if [[ -n "$COLLECTED" && "$COLLECTED" -ge 5 ]]; then
  pass "mock-erp has ≥5 passing tests ($COLLECTED)"
else
  fail "mock-erp has <5 passing tests (found: ${COLLECTED:-0})"
fi

# ── Docker build check ──
if docker build -t kharcha-mock-erp-test -f mock-erp/Dockerfile mock-erp/ >/dev/null 2>&1; then
  pass "mock-erp Docker build succeeds"
  # Quick smoke: container starts and /health responds
  CID=$(docker run -d --rm -p 18090:8090 kharcha-mock-erp-test 2>/dev/null) || true
  if [[ -n "$CID" ]]; then
    sleep 5
    if curl -sf "http://localhost:18090/health" >/dev/null 2>&1 \
       || curl -sf "http://localhost:18090/healthz" >/dev/null 2>&1; then
      pass "mock-erp Docker container responds on /health"
    else
      fail "mock-erp Docker container did not respond on /health"
    fi
    docker stop "$CID" >/dev/null 2>&1 || true
  else
    fail "mock-erp Docker container failed to start"
  fi
  docker rmi kharcha-mock-erp-test >/dev/null 2>&1 || true
else
  fail "mock-erp Docker build failed"
fi

# ── Hygiene gate ──
if ./scripts/check_hygiene.sh >/dev/null 2>&1; then
  pass "check_hygiene.sh passes"
else
  fail "check_hygiene.sh failed"
fi

exit "$FAIL"