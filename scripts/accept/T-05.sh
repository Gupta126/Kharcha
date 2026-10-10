#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "Running accept checks for T-05..."

echo "Checking backend pyjwt dependency..."
grep "pyjwt" backend/pyproject.toml >/dev/null || { echo "FAIL: pyjwt not found in backend pyproject.toml"; exit 1; }

echo "Running tests..."
cd backend
uv run --env-file ../.env.dev pytest -q tests/test_auth.py || { echo "FAIL: test_auth.py failed"; exit 1; }
cd ..

echo "Running seeding..."
make seed-dev || { echo "FAIL: make seed-dev failed"; exit 1; }

echo "Checking DB state for seeded data..."
cd backend
uv run --env-file ../.env.dev python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.settings import settings

async def check():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT count(*) FROM employees;'))
        count = res.scalar()
        if count != 4:
            raise Exception('Expected 4 employees')
        res = await conn.execute(text('SELECT count(*) FROM policies;'))
        count = res.scalar()
        if count != 1:
            raise Exception('Expected 1 policy')
    await engine.dispose()
asyncio.run(check())
" || { echo "FAIL: Seeding did not populate db correctly"; exit 1; }

echo "PASS"
