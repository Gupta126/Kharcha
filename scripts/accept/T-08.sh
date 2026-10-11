#!/bin/bash
set -euo pipefail

echo "Running acceptance script for T-08..."
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

TMP_DIR="$(mktemp -d /tmp/kharcha_t08_test_XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "1) Checking files exist..."
test -f backend/app/schemas/receipt.py
test -f backend/app/services/validators.py
test -f backend/tests/test_validators.py

echo "2) Running pytest in backend on test_validators.py..."
TEST_OUTPUT=$(cd backend && uv run --env-file ../.env.dev pytest -v tests/test_validators.py)
echo "$TEST_OUTPUT"

# Verify test count >= 20
PASSED_COUNT=$(echo "$TEST_OUTPUT" | grep -oE '[0-9]+ passed' | awk '{print $1}')
echo "Passed tests count: $PASSED_COUNT"
if [ "$PASSED_COUNT" -lt 20 ]; then
  echo "FAIL: Expected at least 20 passed tests, got $PASSED_COUNT"
  exit 1
fi

echo "3) Running explicit contract vector and model validation checks..."
uv run --project backend --env-file .env.dev python - <<PYCHECK
import json
import os
import sys
from pathlib import Path
from pydantic import ValidationError

# Add backend to sys.path
backend_path = Path("$REPO_ROOT") / "backend"
sys.path.insert(0, str(backend_path))

from app.schemas.receipt import ExtractedReceipt
from app.services.validators import (
    validate_gstin,
    validate_tax_math,
)

# 1. GSTIN vectors
gstin_file = Path("$REPO_ROOT") / "contracts" / "test-vectors" / "gstin.json"
with open(gstin_file, encoding="utf-8") as f:
    gstin_data = json.load(f)
for case in gstin_data["cases"]:
    val = case["gstin"]
    expected = case["valid"]
    actual = validate_gstin(val)
    assert actual == expected, f"GSTIN vector failed for {val}: expected {expected}, got {actual}"
print(f"Validated {len(gstin_data['cases'])} GSTIN vectors.")

# 2. Tax math vectors
tax_file = Path("$REPO_ROOT") / "contracts" / "test-vectors" / "tax_math.json"
with open(tax_file, encoding="utf-8") as f:
    tax_data = json.load(f)
for case in tax_data["cases"]:
    res = validate_tax_math(
        taxable_paise=case["taxable"],
        cgst_paise=case["cgst"],
        sgst_paise=case["sgst"],
        igst_paise=case["igst"],
        total_paise=case["total"],
    )
    assert res == case["expect"], f"Tax math vector failed for {case['name']}: expected {case['expect']}, got {res}"
print(f"Validated {len(tax_data['cases'])} Tax Math vectors.")

# 3. receipt_example.json validates against ExtractedReceipt
receipt_file = Path("$REPO_ROOT") / "contracts" / "test-vectors" / "receipt_example.json"
with open(receipt_file, encoding="utf-8") as f:
    example_dict = json.load(f)
receipt_obj = ExtractedReceipt.model_validate(example_dict)
assert receipt_obj.doc_id == "d_8f21"
print("receipt_example.json successfully validated against ExtractedReceipt.")

# 4. Modified copy missing required field fails validation
invalid_dict = dict(example_dict)
del invalid_dict["total"]
try:
    ExtractedReceipt.model_validate(invalid_dict)
    raise AssertionError("Expected ValidationError when missing required field 'total', but succeeded")
except ValidationError:
    print("Missing required field correctly rejected by ExtractedReceipt.")

# 5. Generated GSTINs from data.generator all validate
os.system("uv run --project eval python -m data.generator --n 20 --out $TMP_DIR > /dev/null")
import csv
with open("$TMP_DIR/labels.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    gen_rows = list(reader)

assert len(gen_rows) == 20
for r in gen_rows:
    assert validate_gstin(r["gstin"]), f"Generated GSTIN invalid: {r['gstin']}"
print(f"All {len(gen_rows)} freshly generated GSTINs validated.")
PYCHECK

echo "4) Checking ruff in backend..."
(cd backend && uv run ruff check . && uv run ruff format --check .)

echo "5) Running hygiene check..."
./scripts/check_hygiene.sh

echo "PASS: All T-08 acceptance checks passed."
