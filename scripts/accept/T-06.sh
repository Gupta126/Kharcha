#!/bin/bash
set -euo pipefail

echo "Running acceptance script for T-06..."

echo "1) Checking backend settings..."
grep -q "QUEUE_PREFIX" backend/app/core/settings.py
grep -q "TEST_DATABASE_URL" backend/app/core/settings.py

echo "2) Checking forensics placeholder..."
test -f forensics/pyproject.toml
test -f forensics/app/main.py
test -f forensics/Dockerfile

echo "3) Checking mock-erp Dockerfile..."
test -f mock-erp/Dockerfile

echo "4) Checking gateway Dockerfile..."
test -f gateway/Dockerfile

echo "5) Checking backend requirements for rq..."
grep -q "rq" backend/pyproject.toml

echo "6) Running Docker compose config..."
docker compose --env-file .env.example -f deploy/server/docker-compose.yml config -q

echo "7) Testing forensics Dockerfile..."
docker build -t kharcha-forensics-test ./forensics
docker run --rm -d -p 8085:8085 --name forensics_test kharcha-forensics-test
sleep 3
curl -sf http://127.0.0.1:8085/health > /dev/null || (docker rm -f forensics_test; exit 1)
docker rm -f forensics_test

echo "8) Testing gateway Dockerfile..."
docker build -t kharcha-gateway-test ./gateway
docker run -d -p 4000:4000 -e LITELLM_DANGEROUSLY_PERMIT_WEAK_OR_UNSET_MASTER_KEY=true --name gateway_test kharcha-gateway-test
sleep 15
curl -sf http://127.0.0.1:4000/health > /dev/null || (docker logs gateway_test; docker rm -f gateway_test; exit 1)
docker rm -f gateway_test

echo "9) Testing dev API healthz..."
make dev-api &
API_PID=$!
sleep 5
curl -sf 127.0.0.1:8001/v1/healthz > /dev/null || (kill $API_PID; exit 1)
kill $API_PID

echo "10) Testing dev worker..."
make dev-worker &
WORKER_PID=$!
sleep 5
if ! kill -0 $WORKER_PID 2>/dev/null; then
    echo "dev-worker failed to start or died"
    exit 1
fi
kill $WORKER_PID

echo "11) Running ruff and pytest in backend and forensics..."
(cd backend && uv run ruff check . && uv run --env-file ../.env.dev pytest -q)
(cd forensics && uv run ruff check . && uv run pytest -q)

echo "12) Running check_hygiene.sh..."
./scripts/check_hygiene.sh

echo "PASS: All T-06 acceptance checks passed."
