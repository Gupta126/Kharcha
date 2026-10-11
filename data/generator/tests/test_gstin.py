"""Tests for GSTIN validation and generation."""

import json
from pathlib import Path

from data.generator.gstin import generate_synthetic_gstin, validate_gstin


def test_gstin_test_vectors() -> None:
    vectors_file = Path(__file__).resolve().parents[3] / "contracts" / "test-vectors" / "gstin.json"
    with open(vectors_file, encoding="utf-8") as f:
        data = json.load(f)

    for case in data["cases"]:
        gstin = case["gstin"]
        expected = case["valid"]
        assert validate_gstin(gstin) == expected, f"Failed for {gstin}: expected {expected}"


def test_generate_synthetic_gstin() -> None:
    for _ in range(50):
        gstin = generate_synthetic_gstin()
        assert validate_gstin(gstin), f"Generated GSTIN is invalid: {gstin}"
