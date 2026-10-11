"""Tests for receipt schema and SPEC §5 validators."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.receipt import ExtractedReceipt
from app.services.validators import (
    canonicalize_vendor,
    normalize_amount_to_paise,
    validate_date_sanity,
    validate_gstin,
    validate_tax_math,
)

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts" / "test-vectors"


def load_gstin_cases():
    with open(CONTRACTS_DIR / "gstin.json", encoding="utf-8") as f:
        return json.load(f)["cases"]


def load_tax_math_cases():
    with open(CONTRACTS_DIR / "tax_math.json", encoding="utf-8") as f:
        return json.load(f)["cases"]


# 1. GSTIN vector tests
@pytest.mark.parametrize(
    "case",
    load_gstin_cases(),
    ids=lambda c: f"{c['gstin']}_{c['valid']}",
)
def test_gstin_vectors(case):
    gstin = case["gstin"]
    expected = case["valid"]
    assert validate_gstin(gstin) == expected, f"Failed for {gstin}: {case.get('reason')}"


# 2. Tax math vector tests
@pytest.mark.parametrize(
    "case",
    load_tax_math_cases(),
    ids=lambda c: c["name"],
)
def test_tax_math_vectors(case):
    res = validate_tax_math(
        taxable_paise=case["taxable"],
        cgst_paise=case["cgst"],
        sgst_paise=case["sgst"],
        igst_paise=case["igst"],
        total_paise=case["total"],
    )
    assert res == case["expect"], f"Failed for {case['name']}: expected {case['expect']}, got {res}"


# 3. Receipt schema validation tests
def test_receipt_example_validates():
    with open(CONTRACTS_DIR / "receipt_example.json", encoding="utf-8") as f:
        data = json.load(f)
    receipt = ExtractedReceipt.model_validate(data)
    assert receipt.doc_id == "d_8f21"
    assert receipt.doc_type == "meal"
    assert receipt.total.value_paise == 164000
    assert receipt.vendor.value == "Barbeque Nation, Koregaon Park"


def test_receipt_missing_required_fields_fails():
    with open(CONTRACTS_DIR / "receipt_example.json", encoding="utf-8") as f:
        data = json.load(f)

    # Missing total
    bad_data = dict(data)
    del bad_data["total"]
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate(bad_data)

    # Missing doc_id
    bad_data = dict(data)
    del bad_data["doc_id"]
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate(bad_data)

    # Missing vendor
    bad_data = dict(data)
    del bad_data["vendor"]
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate(bad_data)


def test_receipt_forbids_extra_fields():
    with open(CONTRACTS_DIR / "receipt_example.json", encoding="utf-8") as f:
        data = json.load(f)
    bad_data = dict(data)
    bad_data["unknown_extra_field"] = "malicious"
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate(bad_data)


def test_receipt_field_constraints():
    with open(CONTRACTS_DIR / "receipt_example.json", encoding="utf-8") as f:
        data = json.load(f)

    # Invalid confidence > 1.0
    bad_data = dict(data)
    bad_data["vendor"] = dict(bad_data["vendor"])
    bad_data["vendor"]["conf"] = 1.5
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate(bad_data)

    # Invalid bbox length != 4
    bad_data = dict(data)
    bad_data["vendor"] = dict(bad_data["vendor"])
    bad_data["vendor"]["bbox"] = [1, 2, 3]
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate(bad_data)

    # Invalid time pattern
    bad_data = dict(data)
    bad_data["time"] = {"value": "25:70", "conf": 0.9}
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate(bad_data)


# 4. Date sanity tests
def test_date_sanity_valid():
    ref = date(2026, 10, 10)
    # Same day
    ok, status = validate_date_sanity(date(2026, 10, 10), reference_date=ref)
    assert ok and status == "ok"
    # 1 day in the future (within tolerance)
    ok, status = validate_date_sanity(date(2026, 10, 11), reference_date=ref)
    assert ok and status == "ok"
    # 30 days in the past
    ok, status = validate_date_sanity(date(2026, 9, 10), reference_date=ref)
    assert ok and status == "ok"


def test_date_sanity_future():
    ref = date(2026, 10, 10)
    # 2 days in the future
    ok, status = validate_date_sanity(date(2026, 10, 12), reference_date=ref)
    assert not ok and status == "future_date"


def test_date_sanity_older_than_60_days():
    ref = date(2026, 10, 10)
    # 61 days ago (August 10, 2026 is 61 days before Oct 10, 2026)
    ok, status = validate_date_sanity(date(2026, 8, 10), reference_date=ref)
    assert not ok and status == "older_than_60_days"


# 5. Amount normaliser tests
@pytest.mark.parametrize(
    "input_val,expected_paise",
    [
        (150, 15000),
        (150.50, 15050),
        ("150", 15000),
        ("1,500.50", 150050),
        ("₹1,500", 150000),
        ("Rs. 250.75", 25075),
        ("INR 999.00", 99900),
    ],
)
def test_normalize_amount_to_paise(input_val, expected_paise):
    assert normalize_amount_to_paise(input_val) == expected_paise


# 6. Vendor canonicaliser tests
@pytest.mark.parametrize(
    "raw_vendor,expected_canonical",
    [
        ("Uber India Technologies Pvt Ltd", "Uber India"),
        ("ANI Technologies Pvt Ltd (Ola)", "Ola"),
        ("InterGlobe Aviation Ltd (IndiGo)", "IndiGo"),
        ("Barbeque Nation Hospitality Ltd", "Barbeque Nation Hospitality"),
        ("Cafe Coffee Day,  Bangalore ", "Cafe Coffee Day Bangalore"),
    ],
)
def test_canonicalize_vendor(raw_vendor, expected_canonical):
    assert canonicalize_vendor(raw_vendor) == expected_canonical
