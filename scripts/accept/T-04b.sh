#!/usr/bin/env bash
# scripts/accept/T-04b.sh
# Acceptance test script for T-04b: Schema drift fix
set -euo pipefail

echo "Running acceptance script for T-04b..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# 1) Check deliver files exist
echo "1) Checking required deliver files exist..."
test -f backend/alembic/versions/0002_schema_alignment.py || { echo "FAIL: 0002_schema_alignment.py missing"; exit 1; }
test -f scripts/schema_diff.py || { echo "FAIL: scripts/schema_diff.py missing"; exit 1; }
test -f backend/tests/test_schema_matches_sql.py || { echo "FAIL: test_schema_matches_sql.py missing"; exit 1; }
echo "PASS: Deliver files exist."

# 2) Run alembic upgrade head on kharcha_dev
echo "2) Running alembic upgrade head on kharcha_dev..."
cd "$REPO_ROOT/backend"
uv run --env-file ../.env.dev alembic upgrade head
cd "$REPO_ROOT"
echo "PASS: alembic upgrade head succeeded on kharcha_dev."

# 3) Check schema_diff on kharcha_dev
echo "3) Running scripts/schema_diff.py on kharcha_dev..."
python3 scripts/schema_diff.py kharcha_dev
echo "PASS: scripts/schema_diff.py on kharcha_dev found no differences."

# 4) Verify seed counts in kharcha_dev are preserved (4 employees, 14 entitlements)
echo "4) Verifying seed counts preserved in kharcha_dev..."
cd "$REPO_ROOT/backend"
COUNTS=$(uv run --env-file ../.env.dev python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
async def main():
    async with AsyncSessionLocal() as s:
        emp = (await s.execute(text('SELECT count(*) FROM employees'))).scalar()
        ent = (await s.execute(text('SELECT count(*) FROM entitlements'))).scalar()
        print(f'{emp} {ent}')
asyncio.run(main())
")
cd "$REPO_ROOT"
if [ "$COUNTS" != "4 14" ]; then
    echo "FAIL: Expected 4 employees and 14 entitlements, got: $COUNTS"
    exit 1
fi
echo "PASS: Preserved seed counts (4 employees, 14 entitlements)."

# 5) Test migration rollback and re-upgrade on kharcha_test
echo "5) Testing downgrade to 0001 and re-upgrade to head on kharcha_test..."
cd "$REPO_ROOT/backend"
TEST_DB_URL=$(uv run --env-file ../.env.dev python -c "import os; print(os.environ['TEST_DATABASE_URL'])")
DATABASE_URL="$TEST_DB_URL" uv run --env-file ../.env.dev alembic downgrade 0001
DATABASE_URL="$TEST_DB_URL" uv run --env-file ../.env.dev alembic upgrade head
cd "$REPO_ROOT"
echo "PASS: Downgrade to 0001 and re-upgrade to head works on kharcha_test."

# 6) Run pytest twice
echo "6) Running pytest twice on test_schema_matches_sql.py..."
cd "$REPO_ROOT/backend"
uv run --env-file ../.env.dev pytest -v tests/test_schema_matches_sql.py
uv run --env-file ../.env.dev pytest -v tests/test_schema_matches_sql.py
cd "$REPO_ROOT"
echo "PASS: pytest passed twice."

# 7) Ruff check and format
echo "7) Checking ruff in backend..."
cd "$REPO_ROOT/backend"
uv run ruff check .
uv run ruff format --check .
cd "$REPO_ROOT"
echo "PASS: Ruff clean."

# 8) Hygiene check
echo "8) Running hygiene check..."
./scripts/check_hygiene.sh
echo "PASS: Hygiene check passed."

echo "PASS: All T-04b acceptance checks passed."
