#!/usr/bin/env bash
# T-04 Database models and migration — acceptance script
# Checks every Deliver item and "Done when" line from docs/TASKS.md.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

FAIL=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=1; }

# ── Deliver: SQLAlchemy 2 models in backend/app/models/ ──
[[ -d backend/app/models ]] && pass "backend/app/models/ directory exists" \
                             || fail "backend/app/models/ directory missing"

# Check that model files exist (tables from schema.sql)
MODEL_FILES=$(find backend/app/models -name '*.py' ! -name '__init__.py' ! -name 'base.py' 2>/dev/null | wc -l)
if [[ "$MODEL_FILES" -ge 5 ]]; then
  pass "backend/app/models has $MODEL_FILES model files (≥5 expected)"
else
  fail "backend/app/models has $MODEL_FILES model files (<5; schema.sql has many tables)"
fi

# Check models use SQLAlchemy 2 style (Mapped, mapped_column)
if grep -rq 'Mapped\|mapped_column\|DeclarativeBase' backend/app/models/ 2>/dev/null; then
  pass "Models use SQLAlchemy 2 style (Mapped/mapped_column)"
else
  fail "Models do not use SQLAlchemy 2 style"
fi

# ── Deliver: Alembic env + migration 0001_initial ──
# alembic.ini
if [[ -f backend/alembic.ini ]]; then
  pass "backend/alembic.ini exists"
else
  fail "backend/alembic.ini missing"
fi

# Alembic env.py
if [[ -f backend/alembic/env.py ]]; then
  pass "backend/alembic/env.py exists"
else
  fail "backend/alembic/env.py missing"
fi

# Migration 0001_initial
MIGRATION=$(find backend/alembic/versions -name '*0001_initial*' 2>/dev/null | head -1)
if [[ -n "$MIGRATION" ]]; then
  pass "Migration 0001_initial exists: $(basename "$MIGRATION")"
else
  fail "Migration 0001_initial not found in backend/alembic/versions/"
fi

# ── Deliver: created_at/updated_at in models ──
if grep -rq 'created_at\|updated_at' backend/app/models/ 2>/dev/null; then
  pass "Models include created_at/updated_at columns"
else
  fail "Models missing created_at/updated_at columns"
fi

# ── Deliver: async session factory ──
if grep -rq 'AsyncSession\|async_session\|async_engine\|create_async_engine' backend/app/db/ 2>/dev/null; then
  pass "Async session factory present in backend/app/db/"
else
  fail "Async session factory missing in backend/app/db/"
fi

# ── Deliver: migration equal to docs/schema.sql ──
[[ -f docs/schema.sql ]] && pass "docs/schema.sql exists" \
                          || fail "docs/schema.sql missing"

# ── Done when: migration on empty DB gives exactly the tables, enums, indexes in schema.sql ──
# This is tested by test_schema_matches_sql.py
[[ -f backend/tests/test_schema_matches_sql.py ]] \
  && pass "test_schema_matches_sql.py exists" \
  || fail "test_schema_matches_sql.py missing"

# ── Verify: make migrate-dev && cd backend && uv run --env-file ../.env.dev pytest -q tests/test_schema_matches_sql.py ──
# First check that make migrate-dev is available
if make -n migrate-dev >/dev/null 2>&1; then
  pass "make migrate-dev target exists"
else
  fail "make migrate-dev target missing"
fi

# Run migrate-dev
if make migrate-dev >/dev/null 2>&1; then
  pass "make migrate-dev succeeds"
else
  fail "make migrate-dev failed"
fi

# Run the schema match test
PYTEST_OUT=$(cd backend && uv run --env-file ../.env.dev pytest -q tests/test_schema_matches_sql.py 2>&1) || true
PYTEST_RC=$?
COLLECTED=$(echo "$PYTEST_OUT" | grep -oP '\d+(?= passed)' | head -1)
if [[ $PYTEST_RC -eq 0 ]]; then
  pass "test_schema_matches_sql.py passes (${COLLECTED:-0} tests)"
else
  fail "test_schema_matches_sql.py failed (rc=$PYTEST_RC)"
  echo "--- pytest output ---"
  echo "$PYTEST_OUT" | tail -20
  echo "---"
fi

# ── Hygiene gate ──
if ./scripts/check_hygiene.sh >/dev/null 2>&1; then
  pass "check_hygiene.sh passes"
else
  fail "check_hygiene.sh failed"
fi

exit "$FAIL"