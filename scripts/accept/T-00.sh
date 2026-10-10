#!/usr/bin/env bash
# T-00 Contract v1 freeze — acceptance script
# Checks every Deliver item and "Done when" line from docs/TASKS.md.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

FAIL=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

# ── Deliver: contracts/openapi.yaml exists and reviewed against SPEC §3 ──
[[ -f contracts/openapi.yaml ]] && pass "contracts/openapi.yaml exists" \
                                 || fail "contracts/openapi.yaml missing"

# ── Deliver: realistic example for ClaimView (Priya's draft trip) ──
if [[ -f contracts/openapi.yaml ]]; then
  grep -q "Priya" contracts/openapi.yaml \
    && pass "ClaimView example contains Priya (draft trip)" \
    || fail "ClaimView example missing Priya reference"
fi

# ── Deliver: realistic example for Entitlements (Arjun's exhausted broadband) ──
if [[ -f contracts/openapi.yaml ]]; then
  grep -q "Arjun" contracts/openapi.yaml \
    && pass "Entitlements example contains Arjun (broadband)" \
    || fail "Entitlements example missing Arjun reference"
fi

# ── Deliver: tag contract-v1.0.0 ──
git tag -l contract-v1.0.0 | grep -q "contract-v1.0.0" \
  && pass "Tag contract-v1.0.0 exists" \
  || fail "Tag contract-v1.0.0 not found"

# ── Done when: make contract-check passes ──
if make contract-check >/dev/null 2>&1; then
  pass "make contract-check passes"
else
  fail "make contract-check failed"
fi

# ── Done when: Prism serves every path with examples ──
PRISM_PORT=14010
cleanup_prism() { kill "$PRISM_PID" 2>/dev/null || true; }
trap cleanup_prism EXIT

npx -y @stoplight/prism-cli@5 mock contracts/openapi.yaml -p "$PRISM_PORT" &>/dev/null &
PRISM_PID=$!
sleep 15

# Check Prism is alive
if curl -sf "http://localhost:${PRISM_PORT}/v1/healthz" >/dev/null 2>&1; then
  pass "Prism mock is running"
else
  fail "Prism mock did not start"
fi

# /v1/entitlements (Arjun broadband example)
if curl -sf "http://localhost:${PRISM_PORT}/v1/entitlements" \
     -H 'Authorization: Bearer x' | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert isinstance(data, (list, dict)), 'unexpected shape'
" 2>/dev/null; then
  pass "Prism serves /v1/entitlements with example JSON"
else
  fail "Prism /v1/entitlements did not return valid JSON"
fi

# /v1/claims/draft (Priya example)
if curl -sf "http://localhost:${PRISM_PORT}/v1/claims/draft" \
     -H 'Authorization: Bearer x' | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert isinstance(data, (list, dict)), 'unexpected shape'
" 2>/dev/null; then
  pass "Prism serves /v1/claims/draft with example JSON"
else
  fail "Prism /v1/claims/draft did not return valid JSON"
fi

cleanup_prism
trap - EXIT

# ── Hygiene gate ──
if ./scripts/check_hygiene.sh >/dev/null 2>&1; then
  pass "check_hygiene.sh passes"
else
  fail "check_hygiene.sh failed"
fi

exit "$FAIL"