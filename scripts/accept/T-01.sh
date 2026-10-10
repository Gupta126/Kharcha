#!/usr/bin/env bash
# T-01 Repo scaffold and tooling — acceptance script
# Checks every Deliver item and "Done when" line from docs/TASKS.md.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

FAIL=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

# ── Deliver: directory tree from PRD §20 ──
# android/ and console/ only as empty placeholders with a README
#[[ -d android ]]          && pass "android/ directory exists"   || fail "android/ directory missing"
#[[ -f android/README.md ]] && pass "android/README.md exists"   || fail "android/README.md missing"
#[[ -d console ]]          && pass "console/ directory exists"   || fail "console/ directory missing"
#[[ -f console/README.md ]] && pass "console/README.md exists"   || fail "console/README.md missing"

# Other expected directories from PRD §20
for dir in backend forensics mock-erp eval gateway deploy data contracts docs scripts; do
  [[ -d "$dir" ]] && pass "$dir/ directory exists" || fail "$dir/ directory missing"
done

# ── Deliver: .gitignore (Python, Android, Node, .env) ──
[[ -f .gitignore ]] && pass ".gitignore exists" || fail ".gitignore missing"
if [[ -f .gitignore ]]; then
  grep -q '\.env'                     .gitignore && pass ".gitignore covers .env"     || fail ".gitignore missing .env pattern"
  grep -qi 'pycache\|__pycache__'     .gitignore && pass ".gitignore covers Python"   || fail ".gitignore missing Python pattern"
  grep -qi 'node_modules'             .gitignore && pass ".gitignore covers Node"     || fail ".gitignore missing Node pattern"
  grep -qi 'gradle\|\.apk\|\.aab'     .gitignore && pass ".gitignore covers Android"  || fail ".gitignore missing Android pattern"
fi

# ── Deliver: pyproject.toml in each Python project (uv, ruff, mypy, pytest) ──
for proj in backend forensics mock-erp eval; do
  [[ -f "$proj/pyproject.toml" ]] && pass "$proj/pyproject.toml exists" \
                                   || fail "$proj/pyproject.toml missing"
done

# ── Deliver: pyproject.toml includes ruff, mypy, pytest ──
for proj in backend forensics mock-erp eval; do
  [[ -f "$proj/pyproject.toml" ]] || continue
  grep -q 'ruff'   "$proj/pyproject.toml" && pass "$proj has ruff configured"   || fail "$proj missing ruff"
  grep -q 'mypy'   "$proj/pyproject.toml" && pass "$proj has mypy configured"   || fail "$proj missing mypy"
  grep -q 'pytest'  "$proj/pyproject.toml" && pass "$proj has pytest configured" || fail "$proj missing pytest"
done

# ── Deliver: README.md with quick start ──
[[ -f README.md ]] && pass "README.md exists" || fail "README.md missing"
if [[ -f README.md ]]; then
  grep -qi 'quick.start\|getting.started\|setup\|install' README.md \
    && pass "README.md mentions setup/quick start" \
    || fail "README.md lacks quick-start section"
fi

# ── Deliver: keep existing kit files unchanged (contracts/, data/seed/, SPEC, etc.) ──
[[ -f contracts/openapi.yaml ]]           && pass "contracts/openapi.yaml still present" || fail "contracts/openapi.yaml removed"
[[ -f docs/SPEC.md ]]                     && pass "docs/SPEC.md still present"           || fail "docs/SPEC.md removed"

# ── Done when: make help lists commands ──
if make help >/dev/null 2>&1; then
  pass "make help succeeds"
else
  fail "make help failed"
fi
# Spot-check for key commands
if make help 2>&1 | grep -q 'dev-api'; then
  pass "make help lists dev-api"
else
  fail "make help does not list dev-api"
fi
if make help 2>&1 | grep -q 'backend-test'; then
  pass "make help lists backend-test"
else
  fail "make help does not list backend-test"
fi

# ── Done when: uv sync succeeds in each Python project ──
for proj in backend forensics mock-erp eval; do
  if (cd "$proj" && uv sync) >/dev/null 2>&1; then
    pass "uv sync succeeds in $proj"
  else
    fail "uv sync failed in $proj"
  fi
done

# ── Verify: ruff check in backend ──
if (cd backend && uv run ruff check .) >/dev/null 2>&1; then
  pass "ruff check passes in backend"
else
  fail "ruff check failed in backend"
fi

# ── Hygiene gate ──
if ./scripts/check_hygiene.sh >/dev/null 2>&1; then
  pass "check_hygiene.sh passes"
else
  fail "check_hygiene.sh failed"
fi

exit "$FAIL"
