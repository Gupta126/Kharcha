#!/usr/bin/env bash
# scripts/accept/T-10.sh
# Acceptance test script for T-10: Documents API and Tier C extraction
set -euo pipefail

echo "Running acceptance script for T-10..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

APP_PORT=8005
TEST_QUEUE_PREFIX="test-t10-"
CREATED_DOC_IDS=()
CREATED_CLAIM_IDS=()

cleanup() {
  echo "Cleaning up processes and test artifacts..."
  if [ -n "${WORKER_PID:-}" ]; then
    kill "$WORKER_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
  fi
  if [ -n "${APP_PID:-}" ]; then
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi

  # Clean up rows created in kharcha_dev by this acceptance script
  if [ "${#CREATED_DOC_IDS[@]}" -gt 0 ]; then
    echo "Cleaning up test rows in kharcha_dev..."
    for did in "${CREATED_DOC_IDS[@]}"; do
      docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -c "DELETE FROM documents WHERE id = '$did';" >/dev/null 2>&1 || true
    done
  fi
  if [ "${#CREATED_CLAIM_IDS[@]}" -gt 0 ]; then
    for cid in "${CREATED_CLAIM_IDS[@]}"; do
      docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -c "DELETE FROM claims WHERE id = '$cid' AND status = 'draft' AND total_paise = 0 AND (SELECT count(*) FROM expense_lines WHERE claim_id = '$cid') = 0;" >/dev/null 2>&1 || true
    done
  fi
}
trap cleanup EXIT

# 1) Check deliver files exist
echo "1) Checking required deliver files exist..."
test -f backend/app/api/documents.py || { echo "FAIL: backend/app/api/documents.py missing"; exit 1; }
test -f backend/app/services/extraction.py || { echo "FAIL: backend/app/services/extraction.py missing"; exit 1; }
test -f backend/app/workers/extract_document.py || { echo "FAIL: backend/app/workers/extract_document.py missing"; exit 1; }
test -f backend/tests/test_documents.py || { echo "FAIL: backend/tests/test_documents.py missing"; exit 1; }
echo "PASS: Required deliver files exist."

# 2) Verify auth requirement on POST /v1/documents (401 without token)
echo "2) Checking 401 Unauthorized without token..."
cd "$REPO_ROOT/backend"
QUEUE_PREFIX="$TEST_QUEUE_PREFIX" uv run --env-file ../.env.dev uvicorn app.main:app --port "$APP_PORT" --host 127.0.0.1 > /dev/null 2>&1 &
APP_PID=$!

# Wait for server
for _ in {1..20}; do
  if curl -s -m 2 "http://127.0.0.1:$APP_PORT/v1/healthz" > /dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

RESP_401=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
  -H "Content-Type: application/json" \
  -d '{"sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","mime":"image/jpeg","pages":1,"capture_source":"camera_scan","device_tier":"A","extraction":null,"ocr_text":"test"}')
CODE_401=$(echo "$RESP_401" | tail -n1)
BODY_401=$(echo "$RESP_401" | head -n -1)
if [ "$CODE_401" != "401" ]; then
  echo "FAIL: Expected 401 without token, got $CODE_401. Body: $BODY_401"
  exit 1
fi
echo "PASS: 401 Unauthorized returned when token is missing."

# 3) Login as priya@kharcha.test to get JWT token
echo "3) Logging in as priya@kharcha.test..."
LOGIN_RESP=$(curl -s -X POST "http://127.0.0.1:$APP_PORT/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"priya@kharcha.test"}')
TOKEN=$(echo "$LOGIN_RESP" | jq -r '.token // empty')
PRIYA_ID=$(echo "$LOGIN_RESP" | jq -r '.employee_id // empty')
if [ -z "$TOKEN" ] || [ -z "$PRIYA_ID" ]; then
  echo "FAIL: Login failed. Response: $LOGIN_RESP"
  exit 1
fi
echo "PASS: Logged in as priya (id: $PRIYA_ID)."

# 4) Test 422 on invalid body
echo "4) Checking 422 Validation error on invalid body..."
RESP_422=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sha256":"invalid-short-hash"}')
CODE_422=$(echo "$RESP_422" | tail -n1)
if [ "$CODE_422" != "422" ]; then
  echo "FAIL: Expected 422 for invalid body, got $CODE_422"
  exit 1
fi
echo "PASS: 422 Validation error returned on invalid body."

# 5) Path 1: POST document with extraction provided (Tier A/B) -> 201 extracted
echo "5) Testing Path 1 (extraction provided -> 201 extracted)..."
SHA_PATH1="aa11bb22cc33dd44ee55ff667788990011223344556677889900aabbccddeeff"
RECEIPT_JSON=$(cat "$REPO_ROOT/contracts/test-vectors/receipt_example.json")

BODY_PATH1=$(jq -nc \
  --arg sha "$SHA_PATH1" \
  --argjson ext "$RECEIPT_JSON" \
  '{sha256: $sha, mime: "image/jpeg", pages: 1, capture_source: "camera_scan", device_tier: "A", extraction: $ext, trust_signals: []}')

RESP_P1=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$BODY_PATH1")
CODE_P1=$(echo "$RESP_P1" | tail -n1)
DATA_P1=$(echo "$RESP_P1" | head -n -1)

if [ "$CODE_P1" != "201" ]; then
  echo "FAIL: Path 1 expected 201, got $CODE_P1. Body: $DATA_P1"
  exit 1
fi

DOC_ID_P1=$(echo "$DATA_P1" | jq -r '.document_id')
STATUS_P1=$(echo "$DATA_P1" | jq -r '.status')
CLAIM_ID_P1=$(echo "$DATA_P1" | jq -r '.claim_id')
LINE_ID_P1=$(echo "$DATA_P1" | jq -r '.line_id')

if [ "$STATUS_P1" != "extracted" ] || [ -z "$DOC_ID_P1" ] || [ -z "$LINE_ID_P1" ]; then
  echo "FAIL: Path 1 invalid response structure: $DATA_P1"
  exit 1
fi
CREATED_DOC_IDS+=("$DOC_ID_P1")
CREATED_CLAIM_IDS+=("$CLAIM_ID_P1")

# Verify in DB: documents, extracted_fields, expense_lines, claims
DB_VERIFY_P1=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "
  SELECT d.sha256, el.amount_paise, el.vendor, el.expense_date, el.category, c.status
  FROM documents d
  JOIN expense_lines el ON el.document_id = d.id
  JOIN claims c ON c.id = d.claim_id
  WHERE d.id = '$DOC_ID_P1';
")
IFS='|' read -r DB_SHA DB_AMT DB_VENDOR DB_DATE DB_CAT DB_CSTATUS <<< "$DB_VERIFY_P1"

if [ "$DB_SHA" != "$SHA_PATH1" ] || [ "$DB_AMT" != "164000" ] || [ "$DB_DATE" != "2026-10-13" ] || [ "$DB_CAT" != "meal" ]; then
  echo "FAIL: Path 1 DB verification mismatch: $DB_VERIFY_P1"
  exit 1
fi
echo "PASS: Path 1 stored document, line (total 164000, date 2026-10-13, meal) immediately."

# 6) Idempotency: Repeat same sha256 for same employee -> 200, same IDs, no new rows
echo "6) Testing Idempotency (repeat same sha256 -> 200 with same IDs)..."
DOCS_COUNT_PRE=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "SELECT count(*) FROM documents;")
LINES_COUNT_PRE=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "SELECT count(*) FROM expense_lines;")

RESP_IDEMP=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$BODY_PATH1")
CODE_IDEMP=$(echo "$RESP_IDEMP" | tail -n1)
DATA_IDEMP=$(echo "$RESP_IDEMP" | head -n -1)

if [ "$CODE_IDEMP" != "200" ]; then
  echo "FAIL: Idempotent repeat expected 200, got $CODE_IDEMP. Body: $DATA_IDEMP"
  exit 1
fi

DOC_ID_IDEMP=$(echo "$DATA_IDEMP" | jq -r '.document_id')
CLAIM_ID_IDEMP=$(echo "$DATA_IDEMP" | jq -r '.claim_id')
LINE_ID_IDEMP=$(echo "$DATA_IDEMP" | jq -r '.line_id')

if [ "$DOC_ID_IDEMP" != "$DOC_ID_P1" ] || [ "$CLAIM_ID_IDEMP" != "$CLAIM_ID_P1" ] || [ "$LINE_ID_IDEMP" != "$LINE_ID_P1" ]; then
  echo "FAIL: Idempotent IDs do not match! Original: $DOC_ID_P1/$CLAIM_ID_P1/$LINE_ID_P1, Got: $DOC_ID_IDEMP/$CLAIM_ID_IDEMP/$LINE_ID_IDEMP"
  exit 1
fi

DOCS_COUNT_POST=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "SELECT count(*) FROM documents;")
LINES_COUNT_POST=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "SELECT count(*) FROM expense_lines;")

if [ "$DOCS_COUNT_PRE" != "$DOCS_COUNT_POST" ] || [ "$LINES_COUNT_PRE" != "$LINES_COUNT_POST" ]; then
  echo "FAIL: Idempotency added new rows! Docs: $DOCS_COUNT_PRE -> $DOCS_COUNT_POST, Lines: $LINES_COUNT_PRE -> $LINES_COUNT_POST"
  exit 1
fi
echo "PASS: Idempotency returns 200 with identical IDs and zero new rows."

# Stop app before worker tests
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
unset APP_PID

# 7) Path 2: Tier C extraction in stub mode (extraction null with ocr_text -> 201 queued, worker fills fields)
echo "7) Testing Path 2 (Tier C extraction via worker in stub mode)..."
REDIS_TEST_URL="redis://127.0.0.1:6379/1"
cd "$REPO_ROOT/backend"
REDIS_URL="$REDIS_TEST_URL" QUEUE_PREFIX="$TEST_QUEUE_PREFIX" LLM_MODE="stub" \
  uv run --env-file ../.env.dev uvicorn app.main:app --port "$APP_PORT" --host 127.0.0.1 > /dev/null 2>&1 &
APP_PID=$!

REDIS_URL="$REDIS_TEST_URL" QUEUE_PREFIX="$TEST_QUEUE_PREFIX" LLM_MODE="stub" \
  uv run --env-file ../.env.dev rq worker --url "$REDIS_TEST_URL" "${TEST_QUEUE_PREFIX}extract" > /dev/null 2>&1 &
WORKER_PID=$!

for _ in {1..20}; do
  if curl -s -m 2 "http://127.0.0.1:$APP_PORT/v1/healthz" > /dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

SHA_PATH2="bb22cc33dd44ee55ff6677889900112233445566778899001122334455667788"
OCR_TEXT_P2="Barbeque Nation, Koregaon Park Date: 13/10/2026 Total: Rs 1640.00 Veg buffet x2"

RESP_P2=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"sha256\":\"$SHA_PATH2\",\"mime\":\"image/jpeg\",\"pages\":1,\"capture_source\":\"camera_scan\",\"device_tier\":\"C\",\"extraction\":null,\"ocr_text\":\"$OCR_TEXT_P2\"}")
CODE_P2=$(echo "$RESP_P2" | tail -n1)
DATA_P2=$(echo "$RESP_P2" | head -n -1)

if [ "$CODE_P2" != "201" ]; then
  echo "FAIL: Path 2 expected 201, got $CODE_P2. Body: $DATA_P2"
  exit 1
fi

DOC_ID_P2=$(echo "$DATA_P2" | jq -r '.document_id')
STATUS_P2=$(echo "$DATA_P2" | jq -r '.status')
CLAIM_ID_P2=$(echo "$DATA_P2" | jq -r '.claim_id')

if [ "$STATUS_P2" != "queued" ] || [ -z "$DOC_ID_P2" ]; then
  echo "FAIL: Path 2 expected status 'queued', got: $DATA_P2"
  exit 1
fi
CREATED_DOC_IDS+=("$DOC_ID_P2")
CREATED_CLAIM_IDS+=("$CLAIM_ID_P2")

# Poll database until worker fills expense_lines (up to 30 s)
FILLED=0
for _ in {1..30}; do
  LINE_EXISTS=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "
    SELECT count(*) FROM expense_lines WHERE document_id = '$DOC_ID_P2';
  ")
  if [ "$LINE_EXISTS" -ge 1 ]; then
    FILLED=1
    break
  fi
  sleep 1
done

if [ "$FILLED" -ne 1 ]; then
  echo "FAIL: Worker did not fill expense line within 30 seconds for doc $DOC_ID_P2."
  exit 1
fi
echo "PASS: Path 2 queued job and worker successfully extracted line in stub mode."

# Stop app and worker
kill "$WORKER_PID" 2>/dev/null || true
wait "$WORKER_PID" 2>/dev/null || true
unset WORKER_PID
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
unset APP_PID

# 8) Degraded mode (LLMUnavailable -> needs_confirmation with 3 questions prefilled)
echo "8) Testing Degraded mode (LLM unavailable -> needs_confirmation + 3 questions)..."
UNUSED_PORT=59999
REDIS_URL="$REDIS_TEST_URL" QUEUE_PREFIX="$TEST_QUEUE_PREFIX" LLM_MODE="live" LITELLM_URL="http://127.0.0.1:$UNUSED_PORT" \
  uv run --env-file ../.env.dev uvicorn app.main:app --port "$APP_PORT" --host 127.0.0.1 > /dev/null 2>&1 &
APP_PID=$!

REDIS_URL="$REDIS_TEST_URL" QUEUE_PREFIX="$TEST_QUEUE_PREFIX" LLM_MODE="live" LITELLM_URL="http://127.0.0.1:$UNUSED_PORT" \
  uv run --env-file ../.env.dev rq worker --url "$REDIS_TEST_URL" "${TEST_QUEUE_PREFIX}extract" > /dev/null 2>&1 &
WORKER_PID=$!

for _ in {1..20}; do
  if curl -s -m 2 "http://127.0.0.1:$APP_PORT/v1/healthz" > /dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

SHA_DEGRADED="cc33dd44ee55ff66778899001122334455667788990011223344556677889900"
OCR_TEXT_DEG="Taj Hotel, Mumbai Date: 2026-10-15 Total: Rs 4500.00 Room stay"

RESP_DEG=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"sha256\":\"$SHA_DEGRADED\",\"mime\":\"image/jpeg\",\"pages\":1,\"capture_source\":\"camera_scan\",\"device_tier\":\"C\",\"extraction\":null,\"ocr_text\":\"$OCR_TEXT_DEG\"}")
DOC_ID_DEG=$(echo "$RESP_DEG" | head -n -1 | jq -r '.document_id')
CLAIM_ID_DEG=$(echo "$RESP_DEG" | head -n -1 | jq -r '.claim_id')
CREATED_DOC_IDS+=("$DOC_ID_DEG")
CREATED_CLAIM_IDS+=("$CLAIM_ID_DEG")

# Poll until questions are created (worker attempts call, catches LLMUnavailable, writes questions)
QUESTIONS_CREATED=0
for _ in {1..30}; do
  Q_COUNT=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "
    SELECT count(*) FROM questions q
    JOIN expense_lines el ON el.id = q.line_id
    WHERE el.document_id = '$DOC_ID_DEG';
  ")
  if [ "$Q_COUNT" -ge 3 ]; then
    QUESTIONS_CREATED=1
    break
  fi
  sleep 1
done

if [ "$QUESTIONS_CREATED" -ne 1 ]; then
  echo "FAIL: Degraded mode did not create 3 questions for doc $DOC_ID_DEG."
  exit 1
fi
echo "PASS: Degraded mode marked document needs_confirmation and created 3 confirmation questions."

# Stop app and worker
kill "$WORKER_PID" 2>/dev/null || true
wait "$WORKER_PID" 2>/dev/null || true
unset WORKER_PID
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
unset APP_PID

# 9) Contract test
echo "9) Running API contract test..."
cd "$REPO_ROOT/backend"
uv run --env-file ../.env.dev pytest -q tests/test_contract.py
echo "PASS: Contract test passed."

# 10) Full pytest suite twice
echo "10) Running full backend pytest suite twice..."
uv run --env-file ../.env.dev pytest -q
uv run --env-file ../.env.dev pytest -q
echo "PASS: Full backend pytest suite passed twice."

# 11) Check database isolation and schema match
echo "11) Checking schema match and zero drift..."
cd "$REPO_ROOT"
uv run --project backend python scripts/schema_diff.py kharcha_dev
echo "PASS: Database matches docs/schema.sql."

# 12) Ruff check and format
echo "12) Checking ruff in backend..."
cd "$REPO_ROOT/backend"
uv run ruff check .
uv run ruff format --check .
echo "PASS: Ruff clean."

# 13) Hygiene check (no WARN)
echo "13) Running hygiene check..."
cd "$REPO_ROOT"
./scripts/check_hygiene.sh
echo "PASS: Hygiene check passed."

echo "PASS: All T-10 acceptance checks passed."
EOF
