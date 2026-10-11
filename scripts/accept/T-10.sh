#!/usr/bin/env bash
# scripts/accept/T-10.sh
# Acceptance test script for T-10: Documents API and Tier C extraction
# Runs EVERY check and prints PASS/FAIL, exiting non-zero at the end if any check failed.
set -uo pipefail

echo "Running acceptance script for T-10..."

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

APP_PORT=8005
TEST_QUEUE_PREFIX="test-t10-"
CREATED_DOC_IDS=()
CREATED_CLAIM_IDS=()
FAILURES=0

record_pass() {
  echo "PASS: $1"
}

record_fail() {
  echo "FAIL: $1"
  FAILURES=$((FAILURES + 1))
}

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
files_ok=1
for f in backend/app/api/documents.py backend/app/services/extraction.py backend/app/workers/extract_document.py backend/tests/test_documents.py; do
  if [ ! -f "$f" ]; then
    echo "  -> Missing file: $f"
    files_ok=0
  fi
done
if [ "$files_ok" -eq 1 ]; then
  record_pass "Required deliver files exist."
else
  record_fail "One or more required deliver files missing."
fi

# 2) Start app on port 8005
echo "2) Checking 401 Unauthorized without token..."
cd "$REPO_ROOT/backend"
QUEUE_PREFIX="$TEST_QUEUE_PREFIX" uv run --env-file ../.env.dev uvicorn app.main:app --port "$APP_PORT" --host 127.0.0.1 > /dev/null 2>&1 &
APP_PID=$!

server_ready=0
for _ in {1..25}; do
  if curl -s -m 2 "http://127.0.0.1:$APP_PORT/v1/healthz" > /dev/null 2>&1; then
    server_ready=1
    break
  fi
  sleep 0.2
done

if [ "$server_ready" -eq 1 ]; then
  RESP_401=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
    -H "Content-Type: application/json" \
    -d '{"sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","mime":"image/jpeg","pages":1,"capture_source":"camera_scan","device_tier":"A","extraction":null,"ocr_text":"test"}')
  CODE_401=$(echo "$RESP_401" | tail -n1)
  BODY_401=$(echo "$RESP_401" | head -n -1)
  if [ "$CODE_401" = "401" ]; then
    record_pass "401 Unauthorized returned when token is missing."
  else
    record_fail "Expected 401 without token, got $CODE_401 (Body: $BODY_401)."
  fi
else
  record_fail "App server failed to start on port $APP_PORT."
fi

# 3) Login as priya@kharcha.test to get JWT token
echo "3) Logging in as priya@kharcha.test..."
TOKEN=""
PRIYA_ID=""
if [ "$server_ready" -eq 1 ]; then
  LOGIN_RESP=$(curl -s -X POST "http://127.0.0.1:$APP_PORT/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"priya@kharcha.test"}')
  TOKEN=$(echo "$LOGIN_RESP" | jq -r '.token // empty' 2>/dev/null || true)
  PRIYA_ID=$(echo "$LOGIN_RESP" | jq -r '.employee_id // empty' 2>/dev/null || true)
  if [ -n "$TOKEN" ] && [ -n "$PRIYA_ID" ]; then
    record_pass "Logged in as priya (id: $PRIYA_ID)."
  else
    record_fail "Login failed. Response: $LOGIN_RESP"
  fi
else
  record_fail "Cannot test login: app server not ready."
fi

# 4) Test 422 on invalid body
echo "4) Checking 422 Validation error on invalid body..."
if [ "$server_ready" -eq 1 ] && [ -n "$TOKEN" ]; then
  RESP_422=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"sha256":"invalid-short-hash"}')
  CODE_422=$(echo "$RESP_422" | tail -n1)
  if [ "$CODE_422" = "422" ]; then
    record_pass "422 Validation error returned on invalid body."
  else
    record_fail "Expected 422 for invalid body, got $CODE_422"
  fi
else
  record_fail "Cannot test 422 validation: server or token missing."
fi

# 5) Path 1: POST document with extraction provided (Tier A/B) -> 201 extracted
echo "5) Testing Path 1 (extraction provided -> 201 extracted)..."
DOC_ID_P1=""
CLAIM_ID_P1=""
LINE_ID_P1=""
SHA_PATH1="aa11bb22cc33dd44ee55ff667788990011223344556677889900aabbccddeeff"

if [ "$server_ready" -eq 1 ] && [ -n "$TOKEN" ]; then
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

  if [ "$CODE_P1" = "201" ]; then
    DOC_ID_P1=$(echo "$DATA_P1" | jq -r '.document_id // empty' 2>/dev/null || true)
    STATUS_P1=$(echo "$DATA_P1" | jq -r '.status // empty' 2>/dev/null || true)
    CLAIM_ID_P1=$(echo "$DATA_P1" | jq -r '.claim_id // empty' 2>/dev/null || true)
    LINE_ID_P1=$(echo "$DATA_P1" | jq -r '.line_id // empty' 2>/dev/null || true)

    if [ "$STATUS_P1" = "extracted" ] && [ -n "$DOC_ID_P1" ] && [ -n "$LINE_ID_P1" ]; then
      CREATED_DOC_IDS+=("$DOC_ID_P1")
      CREATED_CLAIM_IDS+=("$CLAIM_ID_P1")

      DB_VERIFY_P1=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "
        SELECT d.sha256, el.amount_paise, el.vendor, el.expense_date, el.category, c.status
        FROM documents d
        JOIN expense_lines el ON el.document_id = d.id
        JOIN claims c ON c.id = d.claim_id
        WHERE d.id = '$DOC_ID_P1';
      " 2>/dev/null || true)
      IFS='|' read -r DB_SHA DB_AMT DB_VENDOR DB_DATE DB_CAT DB_CSTATUS <<< "$DB_VERIFY_P1"

      if [ "$DB_SHA" = "$SHA_PATH1" ] && [ "$DB_AMT" = "164000" ] && [ "$DB_DATE" = "2026-10-13" ] && [ "$DB_CAT" = "meal" ]; then
        record_pass "Path 1 stored document, line (total 164000, date 2026-10-13, meal) immediately."
      else
        record_fail "Path 1 DB verification mismatch: $DB_VERIFY_P1"
      fi
    else
      record_fail "Path 1 invalid response structure: $DATA_P1"
    fi
  else
    record_fail "Path 1 expected 201, got $CODE_P1. Body: $DATA_P1"
  fi
else
  record_fail "Cannot test Path 1: server or token missing."
fi

# 6) Idempotency: Repeat same sha256 for same employee -> 200, same IDs, no new rows
echo "6) Testing Idempotency (repeat same sha256 -> 200 with same IDs)..."
if [ "$server_ready" -eq 1 ] && [ -n "$TOKEN" ] && [ -n "$DOC_ID_P1" ]; then
  DOCS_COUNT_PRE=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "SELECT count(*) FROM documents;" 2>/dev/null || true)
  LINES_COUNT_PRE=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "SELECT count(*) FROM expense_lines;" 2>/dev/null || true)

  RESP_IDEMP=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$BODY_PATH1")
  CODE_IDEMP=$(echo "$RESP_IDEMP" | tail -n1)
  DATA_IDEMP=$(echo "$RESP_IDEMP" | head -n -1)

  if [ "$CODE_IDEMP" = "200" ]; then
    DOC_ID_IDEMP=$(echo "$DATA_IDEMP" | jq -r '.document_id // empty' 2>/dev/null || true)
    CLAIM_ID_IDEMP=$(echo "$DATA_IDEMP" | jq -r '.claim_id // empty' 2>/dev/null || true)
    LINE_ID_IDEMP=$(echo "$DATA_IDEMP" | jq -r '.line_id // empty' 2>/dev/null || true)

    DOCS_COUNT_POST=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "SELECT count(*) FROM documents;" 2>/dev/null || true)
    LINES_COUNT_POST=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "SELECT count(*) FROM expense_lines;" 2>/dev/null || true)

    if [ "$DOC_ID_IDEMP" = "$DOC_ID_P1" ] && [ "$CLAIM_ID_IDEMP" = "$CLAIM_ID_P1" ] && [ "$LINE_ID_IDEMP" = "$LINE_ID_P1" ] && [ "$DOCS_COUNT_PRE" = "$DOCS_COUNT_POST" ] && [ "$LINES_COUNT_PRE" = "$LINES_COUNT_POST" ]; then
      record_pass "Idempotency returns 200 with identical IDs and zero new rows."
    else
      record_fail "Idempotency mismatch: IDs ($DOC_ID_IDEMP vs $DOC_ID_P1) or counts changed ($DOCS_COUNT_PRE -> $DOCS_COUNT_POST, $LINES_COUNT_PRE -> $LINES_COUNT_POST)."
    fi
  else
    record_fail "Idempotent repeat expected 200, got $CODE_IDEMP. Body: $DATA_IDEMP"
  fi
else
  record_fail "Cannot test idempotency: prerequisite Path 1 document not created."
fi

# Stop initial app
if [ -n "${APP_PID:-}" ]; then
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
  unset APP_PID
fi

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

server_p2_ready=0
for _ in {1..25}; do
  if curl -s -m 2 "http://127.0.0.1:$APP_PORT/v1/healthz" > /dev/null 2>&1; then
    server_p2_ready=1
    break
  fi
  sleep 0.2
done

if [ "$server_p2_ready" -eq 1 ] && [ -n "$TOKEN" ]; then
  SHA_PATH2="bb22cc33dd44ee55ff6677889900112233445566778899001122334455667788"
  OCR_TEXT_P2="Barbeque Nation, Koregaon Park Date: 13/10/2026 Total: Rs 1640.00 Veg buffet x2"

  RESP_P2=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"sha256\":\"$SHA_PATH2\",\"mime\":\"image/jpeg\",\"pages\":1,\"capture_source\":\"camera_scan\",\"device_tier\":\"C\",\"extraction\":null,\"ocr_text\":\"$OCR_TEXT_P2\"}")
  CODE_P2=$(echo "$RESP_P2" | tail -n1)
  DATA_P2=$(echo "$RESP_P2" | head -n -1)

  if [ "$CODE_P2" = "201" ]; then
    DOC_ID_P2=$(echo "$DATA_P2" | jq -r '.document_id // empty' 2>/dev/null || true)
    STATUS_P2=$(echo "$DATA_P2" | jq -r '.status // empty' 2>/dev/null || true)
    CLAIM_ID_P2=$(echo "$DATA_P2" | jq -r '.claim_id // empty' 2>/dev/null || true)

    if [ "$STATUS_P2" = "queued" ] && [ -n "$DOC_ID_P2" ]; then
      CREATED_DOC_IDS+=("$DOC_ID_P2")
      CREATED_CLAIM_IDS+=("$CLAIM_ID_P2")

      FILLED=0
      for _ in {1..20}; do
        LINE_EXISTS=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "
          SELECT count(*) FROM expense_lines WHERE document_id = '$DOC_ID_P2';
        " 2>/dev/null || true)
        if [ "${LINE_EXISTS:-0}" -ge 1 ]; then
          FILLED=1
          break
        fi
        sleep 1
      done

      if [ "$FILLED" -eq 1 ]; then
        record_pass "Path 2 queued job and worker successfully extracted line in stub mode."
      else
        record_fail "Worker did not fill expense line within timeout for doc $DOC_ID_P2."
      fi
    else
      record_fail "Path 2 expected status 'queued', got: $DATA_P2"
    fi
  else
    record_fail "Path 2 expected 201, got $CODE_P2. Body: $DATA_P2"
  fi
else
  record_fail "Cannot test Path 2: app server not ready or token missing."
fi

# Stop app and worker
if [ -n "${WORKER_PID:-}" ]; then
  kill "$WORKER_PID" 2>/dev/null || true
  wait "$WORKER_PID" 2>/dev/null || true
  unset WORKER_PID
fi
if [ -n "${APP_PID:-}" ]; then
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
  unset APP_PID
fi

# 8) Degraded mode (LLMUnavailable -> needs_confirmation with 3 questions prefilled)
echo "8) Testing Degraded mode (LLM unavailable -> needs_confirmation + 3 questions)..."
UNUSED_PORT=59999
cd "$REPO_ROOT/backend"
REDIS_URL="$REDIS_TEST_URL" QUEUE_PREFIX="$TEST_QUEUE_PREFIX" LLM_MODE="live" LITELLM_URL="http://127.0.0.1:$UNUSED_PORT" \
  uv run --env-file ../.env.dev uvicorn app.main:app --port "$APP_PORT" --host 127.0.0.1 > /dev/null 2>&1 &
APP_PID=$!

REDIS_URL="$REDIS_TEST_URL" QUEUE_PREFIX="$TEST_QUEUE_PREFIX" LLM_MODE="live" LITELLM_URL="http://127.0.0.1:$UNUSED_PORT" \
  uv run --env-file ../.env.dev rq worker --url "$REDIS_TEST_URL" "${TEST_QUEUE_PREFIX}extract" > /dev/null 2>&1 &
WORKER_PID=$!

server_deg_ready=0
for _ in {1..25}; do
  if curl -s -m 2 "http://127.0.0.1:$APP_PORT/v1/healthz" > /dev/null 2>&1; then
    server_deg_ready=1
    break
  fi
  sleep 0.2
done

if [ "$server_deg_ready" -eq 1 ] && [ -n "$TOKEN" ]; then
  SHA_DEGRADED="cc33dd44ee55ff66778899001122334455667788990011223344556677889900"
  OCR_TEXT_DEG="Taj Hotel, Mumbai Date: 2026-10-15 Total: Rs 4500.00 Room stay"

  RESP_DEG=$(curl -s -w "\n%{http_code}" -X POST "http://127.0.0.1:$APP_PORT/v1/documents" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"sha256\":\"$SHA_DEGRADED\",\"mime\":\"image/jpeg\",\"pages\":1,\"capture_source\":\"camera_scan\",\"device_tier\":\"C\",\"extraction\":null,\"ocr_text\":\"$OCR_TEXT_DEG\"}")
  DATA_DEG=$(echo "$RESP_DEG" | head -n -1)
  DOC_ID_DEG=$(echo "$DATA_DEG" | jq -r '.document_id // empty' 2>/dev/null || true)
  CLAIM_ID_DEG=$(echo "$DATA_DEG" | jq -r '.claim_id // empty' 2>/dev/null || true)

  if [ -n "$DOC_ID_DEG" ]; then
    CREATED_DOC_IDS+=("$DOC_ID_DEG")
    CREATED_CLAIM_IDS+=("$CLAIM_ID_DEG")

    QUESTIONS_CREATED=0
    for _ in {1..20}; do
      Q_COUNT=$(docker exec kharcha-postgres-1 psql -U kharcha -d kharcha_dev -t -A -c "
        SELECT count(*) FROM questions q
        JOIN expense_lines el ON el.id = q.line_id
        WHERE el.document_id = '$DOC_ID_DEG';
      " 2>/dev/null || true)
      if [ "${Q_COUNT:-0}" -ge 3 ]; then
        QUESTIONS_CREATED=1
        break
      fi
      sleep 1
    done

    if [ "$QUESTIONS_CREATED" -eq 1 ]; then
      record_pass "Degraded mode marked document needs_confirmation and created 3 confirmation questions."
    else
      record_fail "Degraded mode did not create 3 questions for doc $DOC_ID_DEG."
    fi
  else
    record_fail "Degraded mode POST failed to return document_id: $DATA_DEG"
  fi
else
  record_fail "Cannot test degraded mode: server not ready or token missing."
fi

# Stop app and worker
if [ -n "${WORKER_PID:-}" ]; then
  kill "$WORKER_PID" 2>/dev/null || true
  wait "$WORKER_PID" 2>/dev/null || true
  unset WORKER_PID
fi
if [ -n "${APP_PID:-}" ]; then
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
  unset APP_PID
fi

# 9) Contract test
echo "9) Running API contract test..."
cd "$REPO_ROOT/backend"
if uv run --env-file ../.env.dev pytest -q tests/test_contract.py; then
  record_pass "Contract test passed."
else
  record_fail "Contract test failed."
fi

# 10) Full pytest suite twice
echo "10) Running full backend pytest suite twice..."
if uv run --env-file ../.env.dev pytest -q && uv run --env-file ../.env.dev pytest -q; then
  record_pass "Full backend pytest suite passed twice."
else
  record_fail "Full backend pytest suite failed."
fi

# 11) Check database isolation and schema match
echo "11) Checking schema match and zero drift..."
cd "$REPO_ROOT"
if uv run --project backend python scripts/schema_diff.py kharcha_dev; then
  record_pass "Database matches docs/schema.sql."
else
  record_fail "Database schema diff detected drift against docs/schema.sql."
fi

# 12) Ruff check and format
echo "12) Checking ruff in backend..."
cd "$REPO_ROOT/backend"
if uv run ruff check . && uv run ruff format --check .; then
  record_pass "Ruff clean."
else
  record_fail "Ruff check or format failed."
fi

# 13) Hygiene check (no WARN)
echo "13) Running hygiene check..."
cd "$REPO_ROOT"
if ./scripts/check_hygiene.sh; then
  record_pass "Hygiene check passed."
else
  record_fail "Hygiene check failed."
fi

echo "Acceptance checks complete. Total failures: $FAILURES."
if [ "$FAILURES" -eq 0 ]; then
  echo "PASS: All T-10 acceptance checks passed."
  exit 0
else
  echo "FAIL: $FAILURES acceptance checks failed."
  exit 1
fi
