"""Tests for synthetic receipt batch generation and label consistency."""

import csv
import hashlib
import tempfile
from pathlib import Path

from data.generator.generator import REQUIRED_TAMPER_TYPES, generate_receipts
from data.generator.gstin import validate_gstin


def file_sha256(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_generate_receipts_consistency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir)
        n = 20
        generate_receipts(n=n, output_dir=out_path, seed=123)

        labels_file = out_path / "labels.csv"
        assert labels_file.exists(), "labels.csv must be created"

        with open(labels_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == n, f"Expected {n} rows, found {len(rows)}"

        # Check files on disk
        files_on_disk = [p for p in out_path.iterdir() if p.name != "labels.csv"]
        assert len(files_on_disk) == n, f"Expected {n} files on disk, found {len(files_on_disk)}"

        by_id = {r["doc_id"]: r for r in rows}
        tamper_found = set()

        for r in rows:
            file_path = out_path / r["file"]
            assert file_path.exists(), f"File {r['file']} must exist on disk"

            # GSTIN validity
            assert validate_gstin(r["gstin"]), f"GSTIN {r['gstin']} must pass checksum"

            # Arithmetic
            total = int(r["total_paise"])
            taxable = int(r["taxable_paise"])
            cgst = int(r["cgst_paise"])
            sgst = int(r["sgst_paise"])
            igst = int(r["igst_paise"])
            assert total == taxable + cgst + sgst + igst, (
                f"Math mismatch for {r['doc_id']}: {total} != {taxable}+{cgst}+{sgst}+{igst}"
            )

            tt = r["tamper_type"]
            if tt != "none":
                tamper_found.add(tt)

            # Check duplicates
            if tt == "exact_duplicate":
                orig = by_id[r["duplicate_of"]]
                assert file_sha256(file_path) == file_sha256(out_path / orig["file"])
            elif tt == "near_duplicate":
                orig = by_id[r["duplicate_of"]]
                assert file_sha256(file_path) != file_sha256(out_path / orig["file"])
                assert r["total_paise"] == orig["total_paise"]
                assert r["vendor"] == orig["vendor"]

        for req_tt in REQUIRED_TAMPER_TYPES:
            assert req_tt in tamper_found, f"Expected tamper type {req_tt} to be present"
