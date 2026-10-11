#!/bin/bash
set -euo pipefail

echo "Running acceptance script for T-07..."
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

TMP_DIR="$(mktemp -d /tmp/kharcha_gen_test_XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "1) Checking generator project files and pins..."
test -f data/generator/pyproject.toml
test -f data/generator/.python-version
grep -q '^3\.12' data/generator/.python-version

echo "2) Generating 20 synthetic receipts into temp folder..."
uv run --project eval python -m data.generator --n 20 --out "$TMP_DIR"
test -f "$TMP_DIR/labels.csv"

echo "3) Validating labels.csv schema, counts, totals, gstin, and tamper types..."
python3 - <<PYCHECK
import csv
import hashlib
import json
import os
import re
import sys

labels_path = os.path.join("$TMP_DIR", "labels.csv")
assert os.path.exists(labels_path), "labels.csv missing"

with open(labels_path, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames or []
    rows = list(reader)

required_columns = [
    "doc_id", "file", "doc_type", "vendor", "date",
    "total_paise", "taxable_paise", "cgst_paise", "sgst_paise",
    "igst_paise", "gstin", "city", "tamper_type", "duplicate_of"
]
for col in required_columns:
    assert col in fieldnames, f"Missing column: {col}"

print(f"Loaded {len(rows)} rows from labels.csv")
assert len(rows) == 20, f"Expected 20 rows, got {len(rows)}"

# Check files exist on disk
disk_files = [f for f in os.listdir("$TMP_DIR") if f != "labels.csv"]
assert len(disk_files) == len(rows), f"File count {len(disk_files)} does not match label count {len(rows)}"

row_by_id = {r["doc_id"]: r for r in rows}

# GSTIN validator
CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHAR_MAP = {c: i for i, c in enumerate(CHARS)}

def validate_gstin(gstin: str) -> bool:
    if not re.match(r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", gstin):
        return False
    state_code = int(gstin[:2])
    if not (1 <= state_code <= 38):
        return False
    s = 0
    for i in range(14):
        v = CHAR_MAP[gstin[i]]
        p = v * (1 if i % 2 == 0 else 2)
        s += (p // 36) + (p % 36)
    check_val = (36 - (s % 36)) % 36
    return CHARS[check_val] == gstin[14]

def file_sha256(fname: str) -> str:
    path = os.path.join("$TMP_DIR", fname)
    with open(path, "rb") as fp:
        return hashlib.sha256(fp.read()).hexdigest()

tamper_types_found = set()
required_tamper_types = {
    "edited_total", "edited_date", "pdf_resaved_with_editor",
    "screenshot", "exact_duplicate", "near_duplicate"
}

for r in rows:
    fpath = os.path.join("$TMP_DIR", r["file"])
    assert os.path.isfile(fpath), f"File listed in labels does not exist: {r['file']}"

    # Check GSTIN
    assert validate_gstin(r["gstin"]), f"Invalid GSTIN checksum: {r['gstin']} for doc {r['doc_id']}"

    # Check Total = Taxable + taxes
    total = int(r["total_paise"])
    taxable = int(r["taxable_paise"])
    cgst = int(r["cgst_paise"])
    sgst = int(r["sgst_paise"])
    igst = int(r["igst_paise"])
    assert total == taxable + cgst + sgst + igst, (
        f"Total mismatch for {r['doc_id']}: {total} != {taxable} + {cgst} + {sgst} + {igst}"
    )

    ttype = r["tamper_type"]
    if ttype and ttype != "none":
        tamper_types_found.add(ttype)

    # Check duplicate invariants
    if ttype == "exact_duplicate":
        orig_id = r["duplicate_of"]
        assert orig_id in row_by_id, f"exact_duplicate {r['doc_id']} missing valid duplicate_of"
        orig_file = row_by_id[orig_id]["file"]
        assert file_sha256(r["file"]) == file_sha256(orig_file), (
            f"exact_duplicate {r['file']} sha256 mismatch with {orig_file}"
        )
    elif ttype == "near_duplicate":
        orig_id = r["duplicate_of"]
        assert orig_id in row_by_id, f"near_duplicate {r['doc_id']} missing valid duplicate_of"
        orig_file = row_by_id[orig_id]["file"]
        assert file_sha256(r["file"]) != file_sha256(orig_file), (
            f"near_duplicate {r['file']} must have different sha256 than {orig_file}"
        )
        assert r["total_paise"] == row_by_id[orig_id]["total_paise"]
        assert r["vendor"] == row_by_id[orig_id]["vendor"]

for expected_tt in required_tamper_types:
    assert expected_tt in tamper_types_found, f"Missing required tamper type in sample: {expected_tt}"

print("All labels, totals, GSTIN checksums, and tamper invariants validated!")
PYCHECK

echo "4) Running generator tests..."
(cd data/generator && uv run pytest -q)

echo "5) Running ruff checks on data/generator and eval..."
(cd data/generator && uv run ruff check . && uv run ruff format --check .)
(cd eval && uv run ruff check . && uv run ruff format --check .)

echo "6) Running hygiene check..."
./scripts/check_hygiene.sh

echo "PASS: All T-07 acceptance checks passed."
