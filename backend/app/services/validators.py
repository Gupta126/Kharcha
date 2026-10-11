"""Validation algorithms implementing SPEC §5."""

import re
from datetime import date, datetime, timedelta

# GSTIN constants
GSTIN_REGEX = re.compile(r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHAR_MAP = {c: i for i, c in enumerate(CHARS)}

# Standard GST tax slabs in India
GST_SLABS: set[float] = {0.0, 5.0, 12.0, 18.0, 28.0}


def validate_gstin(gstin: str) -> bool:
    """Validate GSTIN format, state code (01-38), and mod-36 checksum per SPEC §5."""
    if not isinstance(gstin, str):
        return False
    if not GSTIN_REGEX.match(gstin):
        return False
    state_code = int(gstin[:2])
    if not (1 <= state_code <= 38):
        return False
    s = 0
    for i in range(14):
        char = gstin[i]
        if char not in CHAR_MAP:
            return False
        v = CHAR_MAP[char]
        p = v * (1 if i % 2 == 0 else 2)
        s += (p // 36) + (p % 36)
    check_val = (36 - (s % 36)) % 36
    return CHARS[check_val] == gstin[14]


def validate_tax_math(
    taxable_paise: int | None,
    cgst_paise: int | None,
    sgst_paise: int | None,
    igst_paise: int | None,
    total_paise: int,
) -> str:
    """Validate GST tax math per SPEC §5.

    Returns one of:
      - 'ok'
      - 'cgst_sgst_mismatch'
      - 'mixed_igst_cgst'
      - 'total_mismatch'
      - 'rate_not_slab'
    """
    has_cgst = cgst_paise is not None and cgst_paise > 0
    has_sgst = sgst_paise is not None and sgst_paise > 0
    has_igst = igst_paise is not None and igst_paise > 0

    # Mixed IGST and CGST/SGST check
    if has_igst and (has_cgst or has_sgst):
        return "mixed_igst_cgst"

    # CGST and SGST mismatch check
    # If one is present and the other is absent or 0, or if difference > 1 paise
    cgst_val = cgst_paise if cgst_paise is not None else 0
    sgst_val = sgst_paise if sgst_paise is not None else 0
    igst_val = igst_paise if igst_paise is not None else 0

    if (has_cgst and not has_sgst) or (has_sgst and not has_cgst):
        return "cgst_sgst_mismatch"
    if (has_cgst and has_sgst) and abs(cgst_val - sgst_val) > 1:
        return "cgst_sgst_mismatch"

    total_taxes = cgst_val + sgst_val + igst_val
    taxable_val = taxable_paise if taxable_paise is not None else 0

    # Total mismatch check: taxable + taxes = total within max(100 paise, 0.5% of total)
    tolerance = max(100, int(round(0.005 * total_paise)))
    calculated_total = taxable_val + total_taxes
    if abs(calculated_total - total_paise) > tolerance:
        return "total_mismatch"

    # Implied rate check: taxes / taxable * 100 within 0.5 percentage points of a slab
    if taxable_val > 0 and total_taxes > 0:
        implied_rate = (total_taxes / taxable_val) * 100.0
        min_slab_diff = min(abs(implied_rate - slab) for slab in GST_SLABS)
        if min_slab_diff > 0.5:
            return "rate_not_slab"

    return "ok"


def validate_date_sanity(
    expense_date: date | str,
    reference_date: date | None = None,
) -> tuple[bool, str]:
    """Validate expense date sanity per SPEC §5.

    Rules:
      - not in the future (reference_date + 1 day allowance)
      - older than 60 days (P-AGE-1) is flagged as red / expired
    Returns:
      (is_valid, status)
    """
    ref = reference_date or date.today()
    if isinstance(expense_date, str):
        try:
            exp_date = datetime.strptime(expense_date, "%Y-%m-%d").date()
        except ValueError:
            exp_date = datetime.fromisoformat(expense_date).date()
    else:
        exp_date = expense_date

    # Future date check
    if exp_date > ref + timedelta(days=1):
        return False, "future_date"

    # 60 days age check
    if exp_date < ref - timedelta(days=60):
        return False, "older_than_60_days"

    return True, "ok"


def normalize_amount_to_paise(val: int | float | str) -> int:
    """Normalize a rupee value (string, float, or integer) to integer paise."""
    if isinstance(val, (int, float)):
        return int(round(val * 100))

    if isinstance(val, str):
        # Clean currency symbols, commas, and whitespace
        cleaned = re.sub(r"[₹\$,\s]", "", val)
        cleaned = re.sub(r"^(INR|Rs\.?|re\.?)\s*", "", cleaned, flags=re.IGNORECASE)
        float_val = float(cleaned)
        return int(round(float_val * 100))

    raise TypeError(f"Cannot normalize amount of type {type(val)}")


def canonicalize_vendor(name: str) -> str:
    """Canonicalize vendor name by cleaning legal suffixes, brand aliases, and noise."""
    if not isinstance(name, str):
        return ""

    vendor = name.strip()

    # If there is a parenthetical brand name at the end (e.g. ANI Technologies (Ola)), extract it
    parenthetical_match = re.search(r"\(([^)]+)\)$", vendor)
    if parenthetical_match:
        brand = parenthetical_match.group(1).strip()
        # If the parenthetical is short and looks like a brand name
        if 2 <= len(brand) <= 25 and not any(
            w in brand.lower() for w in ["pvt", "ltd", "branch", "division"]
        ):
            return brand

    # Strip common Indian / corporate legal suffixes
    suffix_pattern = (
        r"\s+(pvt\.?\s*ltd\.?|private\s+limited|technologies|"
        r"tech|ltd\.?|limited|inc\.?|llp|corp\.?|corporation)\b"
    )
    vendor = re.sub(suffix_pattern, "", vendor, flags=re.IGNORECASE)
    # Run once more in case of chained suffixes like "Technologies Pvt Ltd"
    vendor = re.sub(suffix_pattern, "", vendor, flags=re.IGNORECASE)

    # Clean commas, extra hyphens, and whitespace
    vendor = re.sub(r"[,\-_]+", " ", vendor)
    vendor = re.sub(r"\s+", " ", vendor).strip()

    return vendor.title()
