"""Batch synthetic receipt generator orchestrator."""

import csv
import random
from pathlib import Path
from typing import List

from data.generator.models import CATEGORIES, ReceiptRecord, create_synthetic_receipt_record
from data.generator.tamper import render_tampered_document

REQUIRED_TAMPER_TYPES = [
    "edited_total",
    "edited_date",
    "pdf_resaved_with_editor",
    "screenshot",
    "exact_duplicate",
    "near_duplicate",
]

CSV_COLUMNS = [
    "doc_id",
    "file",
    "doc_type",
    "vendor",
    "date",
    "total_paise",
    "taxable_paise",
    "cgst_paise",
    "sgst_paise",
    "igst_paise",
    "gstin",
    "city",
    "tamper_type",
    "duplicate_of",
]


def generate_receipts(
    n: int = 200,
    output_dir: str | Path = "data/generated",
    seed: int = 42,
) -> Path:
    """Generate n synthetic receipts with ground-truth labels.csv."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)

    # Determine tamper plan for n items
    # Always guarantee at least one of each tamper type if n >= len(REQUIRED_TAMPER_TYPES)
    tamper_plan: List[str] = []
    if n >= 2 + len(REQUIRED_TAMPER_TYPES):
        tamper_plan = ["none", "none"]
        # Add all required tamper types
        rest = list(REQUIRED_TAMPER_TYPES)
        # Add additional occasional tampered variants
        additional_tampered_count = int((n - 2 - len(REQUIRED_TAMPER_TYPES)) * 0.15)
        for _ in range(additional_tampered_count):
            rest.append(rng.choice(REQUIRED_TAMPER_TYPES))
        while len(rest) < (n - 2):
            rest.append("none")
        rng.shuffle(rest)
        tamper_plan.extend(rest)
    elif n >= len(REQUIRED_TAMPER_TYPES):
        tamper_plan.extend(REQUIRED_TAMPER_TYPES)
        while len(tamper_plan) < n:
            tamper_plan.append("none")
    else:
        tamper_plan = ["none"] * n

    records: List[ReceiptRecord] = []

    for i in range(n):
        doc_id = f"doc_{i + 1:04d}"
        doc_type = CATEGORIES[i % len(CATEGORIES)]
        ttype = tamper_plan[i]

        orig_record: ReceiptRecord | None = None
        duplicate_of = ""

        if ttype in ("exact_duplicate", "near_duplicate"):
            # Select an earlier untampered record to duplicate
            candidates = [r for r in records if r.tamper_type == "none"]
            orig_record = rng.choice(candidates) if candidates else records[0]
            duplicate_of = orig_record.doc_id

            # Create duplicate record matching original's transaction data
            ext = orig_record.file.split(".")[-1]
            file_name = f"{doc_id}_{orig_record.doc_type}_dup.{ext}"
            rec = ReceiptRecord(
                doc_id=doc_id,
                file=file_name,
                doc_type=orig_record.doc_type,
                vendor=orig_record.vendor,
                date=orig_record.date,
                total_paise=orig_record.total_paise,
                taxable_paise=orig_record.taxable_paise,
                cgst_paise=orig_record.cgst_paise,
                sgst_paise=orig_record.sgst_paise,
                igst_paise=orig_record.igst_paise,
                gstin=orig_record.gstin,
                city=orig_record.city,
                tamper_type=ttype,
                duplicate_of=duplicate_of,
                line_items=orig_record.line_items,
                invoice_no=orig_record.invoice_no,
            )
        else:
            rec = create_synthetic_receipt_record(
                doc_id=doc_id,
                doc_type=doc_type,
                tamper_type=ttype,
                rng=rng,
            )
            # Enforce specific extension for certain tamper types
            if ttype == "pdf_resaved_with_editor" and not rec.file.endswith(".pdf"):
                rec.file = f"{doc_id}_{doc_type}.pdf"
            elif ttype == "screenshot" and not rec.file.endswith(".png"):
                rec.file = f"{doc_id}_{doc_type}.png"

        # Render document to disk
        render_tampered_document(
            record=rec,
            output_dir=out_path,
            original_target_record=orig_record,
            rng=rng,
        )
        records.append(rec)

    # Write labels.csv
    labels_path = out_path / "labels.csv"
    with open(labels_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    "doc_id": r.doc_id,
                    "file": r.file,
                    "doc_type": r.doc_type,
                    "vendor": r.vendor,
                    "date": r.date,
                    "total_paise": r.total_paise,
                    "taxable_paise": r.taxable_paise,
                    "cgst_paise": r.cgst_paise,
                    "sgst_paise": r.sgst_paise,
                    "igst_paise": r.igst_paise,
                    "gstin": r.gstin,
                    "city": r.city,
                    "tamper_type": r.tamper_type,
                    "duplicate_of": r.duplicate_of,
                }
            )

    return out_path
