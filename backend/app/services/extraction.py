"""Service functions for processing receipts, storing extracted fields, and degraded mode."""

import json
import logging
import re
from datetime import date, datetime
from typing import Any

import uuid6
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import Claim
from app.models.document import Document
from app.models.expense_line import ExpenseLine
from app.models.extracted_field import ExtractedField
from app.models.question import Question
from app.schemas.receipt import ExtractedReceipt
from app.services.validators import validate_gstin, validate_tax_math

logger = logging.getLogger(__name__)


def parse_ocr_heuristics(ocr_text: str) -> dict[str, Any]:
    """Extract vendor, date, and total from OCR text using regex heuristics per SPEC §6."""
    text_data = ocr_text or ""
    lines = [line.strip() for line in text_data.splitlines() if line.strip()]

    # 1. Vendor heuristic: first non-empty line with letters
    vendor = "Unknown Vendor"
    for line in lines:
        if re.search(r"[a-zA-Z]{3,}", line):
            # Clean common noise
            cleaned = re.sub(
                r"^(tax invoice|invoice|bill|receipt)[:\s-]*", "", line, flags=re.I
            ).strip()
            if cleaned:
                vendor = cleaned[:100]
                break

    # 2. Date heuristic: search for DD/MM/YYYY, DD-MM-YYYY, or YYYY-MM-DD
    found_date_str = date.today().isoformat()
    # YYYY-MM-DD
    match_iso = re.search(r"\b(20\d{2})[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b", text_data)
    if match_iso:
        y, m, d = match_iso.groups()
        found_date_str = f"{y}-{m}-{d}"
    else:
        # DD/MM/YYYY or DD-MM-YY
        match_dmy = re.search(
            r"\b(0[1-9]|[12]\d|3[01])[-/.](0[1-9]|1[0-2])[-/.](20\d{2}|\d{2})\b", text_data
        )
        if match_dmy:
            d, m, y = match_dmy.groups()
            if len(y) == 2:
                y = f"20{y}"
            found_date_str = f"{y}-{m}-{d}"

    # 3. Total heuristic: search for total amount in Rs / INR / Total: ...
    amount_paise = 0
    # Match patterns like Total: Rs. 1640.00 or Rs 1,640.00 or Total 1640
    patterns = [
        (
            r"(?:total|net amount|grand total|amount paid|amount)"
            r"[:\s]*(?:rs\.?|inr)?\s*([0-9,]+(?:\.[0-9]{1,2})?)"
        ),
        r"(?:rs\.?|inr)\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        r"\b([0-9,]+\.[0-9]{2})\b",
    ]
    for pat in patterns:
        matches = re.findall(pat, text_data, flags=re.IGNORECASE)
        if matches:
            # Take the largest match if multiple or the last
            candidates = []
            for m in matches:
                clean_num = m.replace(",", "")
                try:
                    val = float(clean_num)
                    if 0 < val < 10000000:  # reasonable amount filter
                        candidates.append(int(round(val * 100)))
                except ValueError:
                    continue
            if candidates:
                amount_paise = max(candidates)
                break

    return {
        "vendor": vendor,
        "expense_date": found_date_str,
        "amount_paise": amount_paise,
    }


async def save_extracted_receipt(
    db: AsyncSession,
    doc: Document,
    claim: Claim,
    receipt: ExtractedReceipt,
    default_source: str,
) -> ExpenseLine:
    """Persist extracted fields and create the expense line from a validated ExtractedReceipt."""
    # 1. Store extracted fields
    fields_to_add: list[ExtractedField] = []

    # vendor
    fields_to_add.append(
        ExtractedField(
            id=uuid6.uuid7(),
            document_id=doc.id,
            name="vendor",
            value=receipt.vendor.value,
            confidence=receipt.vendor.conf,
            bbox=json.dumps(receipt.vendor.bbox) if receipt.vendor.bbox else None,
            source=default_source,
        )
    )

    # date
    fields_to_add.append(
        ExtractedField(
            id=uuid6.uuid7(),
            document_id=doc.id,
            name="date",
            value=receipt.date.value,
            confidence=receipt.date.conf,
            bbox=json.dumps(receipt.date.bbox) if receipt.date.bbox else None,
            source=default_source,
        )
    )

    # total
    fields_to_add.append(
        ExtractedField(
            id=uuid6.uuid7(),
            document_id=doc.id,
            name="total",
            value=str(receipt.total.value_paise),
            confidence=receipt.total.conf,
            bbox=None,
            source=default_source,
        )
    )

    # doc_type
    fields_to_add.append(
        ExtractedField(
            id=uuid6.uuid7(),
            document_id=doc.id,
            name="doc_type",
            value=receipt.doc_type,
            confidence=1.0,
            bbox=None,
            source=default_source,
        )
    )

    # GSTIN (run T-08 checksum validator)
    gstin_val = None
    gstin_checksum_ok = None
    if receipt.gstin:
        gstin_val = receipt.gstin.value
        gstin_checksum_ok = validate_gstin(gstin_val)
        fields_to_add.append(
            ExtractedField(
                id=uuid6.uuid7(),
                document_id=doc.id,
                name="gstin",
                value=gstin_val,
                confidence=1.0 if gstin_checksum_ok else 0.5,
                bbox=None,
                source=default_source,
            )
        )

    # tax (run T-08 tax math validator)
    taxable_paise = None
    cgst_paise = None
    sgst_paise = None
    igst_paise = None
    if receipt.tax:
        taxable_paise = receipt.tax.taxable_paise
        cgst_paise = receipt.tax.cgst_paise
        sgst_paise = receipt.tax.sgst_paise
        igst_paise = receipt.tax.igst_paise
        tax_res = validate_tax_math(
            taxable_paise, cgst_paise, sgst_paise, igst_paise, receipt.total.value_paise
        )
        tax_conf = receipt.tax.conf if receipt.tax.conf is not None else 0.9
        fields_to_add.append(
            ExtractedField(
                id=uuid6.uuid7(),
                document_id=doc.id,
                name="tax",
                value=json.dumps(
                    {
                        "taxable_paise": taxable_paise,
                        "cgst_paise": cgst_paise,
                        "sgst_paise": sgst_paise,
                        "igst_paise": igst_paise,
                        "math_result": tax_res,
                    }
                ),
                confidence=tax_conf,
                bbox=None,
                source=default_source,
            )
        )

    # line items if present
    if receipt.line_items:
        fields_to_add.append(
            ExtractedField(
                id=uuid6.uuid7(),
                document_id=doc.id,
                name="line_items",
                value=json.dumps([li.model_dump() for li in receipt.line_items]),
                confidence=0.9,
                bbox=None,
                source=default_source,
            )
        )

    for f in fields_to_add:
        db.add(f)

    # 2. Parse expense date
    try:
        exp_date = datetime.strptime(receipt.date.value, "%Y-%m-%d").date()
    except Exception:
        exp_date = date.today()

    # 3. Create expense_lines row
    total_amt = receipt.total.value_paise
    line = ExpenseLine(
        id=uuid6.uuid7(),
        claim_id=claim.id,
        document_id=doc.id,
        category=receipt.doc_type,
        expense_date=exp_date,
        vendor=receipt.vendor.value,
        city=receipt.city.value if receipt.city else None,
        amount_paise=total_amt,
        claimable_paise=total_amt,  # For now claimable = amount per SPEC §3
        cgst_paise=cgst_paise,
        sgst_paise=sgst_paise,
        igst_paise=igst_paise,
        gstin=gstin_val,
        purpose=None,
        attendees="[]",
        excluded_reason=None,
    )
    db.add(line)

    # Update claim total
    claim.total_paise = (claim.total_paise or 0) + total_amt

    await db.flush()
    return line


async def run_degraded_fallback(
    db: AsyncSession,
    doc: Document,
    claim: Claim,
    ocr_text: str,
) -> tuple[ExpenseLine, list[Question]]:
    """Create line with heuristic values and 3 confirmation questions in degraded mode (SPEC §6)."""
    heuristics = parse_ocr_heuristics(ocr_text)

    try:
        exp_date = datetime.strptime(heuristics["expense_date"], "%Y-%m-%d").date()
    except Exception:
        exp_date = date.today()

    amount_paise = heuristics["amount_paise"]
    vendor = heuristics["vendor"]

    # Create line
    line = ExpenseLine(
        id=uuid6.uuid7(),
        claim_id=claim.id,
        document_id=doc.id,
        category="other",
        expense_date=exp_date,
        vendor=vendor,
        city=None,
        amount_paise=amount_paise,
        claimable_paise=amount_paise,
        cgst_paise=None,
        sgst_paise=None,
        igst_paise=None,
        gstin=None,
        purpose=None,
        attendees="[]",
        excluded_reason=None,
    )
    db.add(line)
    await db.flush()

    # Update claim total
    claim.total_paise = (claim.total_paise or 0) + amount_paise

    # Store extracted fields with source='inferred'
    db.add(
        ExtractedField(
            id=uuid6.uuid7(),
            document_id=doc.id,
            name="vendor",
            value=vendor,
            confidence=0.5,
            bbox=None,
            source="inferred",
        )
    )
    db.add(
        ExtractedField(
            id=uuid6.uuid7(),
            document_id=doc.id,
            name="date",
            value=exp_date.isoformat(),
            confidence=0.5,
            bbox=None,
            source="inferred",
        )
    )
    db.add(
        ExtractedField(
            id=uuid6.uuid7(),
            document_id=doc.id,
            name="total",
            value=str(amount_paise),
            confidence=0.5,
            bbox=None,
            source="inferred",
        )
    )

    # Create 3 questions with the pre-filled value as first option per SPEC §6
    # 1. Total
    amount_str = f"Rs {amount_paise / 100:.2f}"
    q_total = Question(
        id=uuid6.uuid7(),
        claim_id=claim.id,
        line_id=line.id,
        field="total",
        prompt="Please confirm the receipt total amount:",
        options=json.dumps([amount_str]),
    )
    # 2. Date
    q_date = Question(
        id=uuid6.uuid7(),
        claim_id=claim.id,
        line_id=line.id,
        field="date",
        prompt="Please confirm the date of the expense:",
        options=json.dumps([exp_date.isoformat()]),
    )
    # 3. Vendor
    q_vendor = Question(
        id=uuid6.uuid7(),
        claim_id=claim.id,
        line_id=line.id,
        field="vendor",
        prompt="Please confirm the vendor / merchant name:",
        options=json.dumps([vendor]),
    )

    db.add(q_total)
    db.add(q_date)
    db.add(q_vendor)

    await db.flush()
    return line, [q_total, q_date, q_vendor]
