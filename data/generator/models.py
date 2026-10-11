"""Data models and synthetic metadata definitions for receipts."""

import datetime
import random
from dataclasses import dataclass, field
from typing import List, Optional

from data.generator.gstin import generate_synthetic_gstin

CATEGORIES = ["cab", "flight", "hotel", "meal", "fuel", "toll", "broadband"]

CITIES = [
    "Mumbai",
    "Bengaluru",
    "Delhi",
    "Hyderabad",
    "Chennai",
    "Pune",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
    "Gurugram",
]

VENDORS_BY_CATEGORY = {
    "cab": [
        "Uber India Technologies Pvt Ltd",
        "ANI Technologies Pvt Ltd (Ola)",
        "BluSmart Mobility",
        "Meru Mobility Tech Pvt Ltd",
    ],
    "flight": [
        "InterGlobe Aviation Ltd (IndiGo)",
        "Air India Ltd",
        "SpiceJet Ltd",
        "Tata SIA Airlines Ltd (Vistara)",
        "SNV Aviation Pvt Ltd (Akasa Air)",
    ],
    "hotel": [
        "The Taj Mahal Palace",
        "ITC Grand Central Hotel",
        "Lemon Tree Premier",
        "Ginger Hotels",
        "Marriott Suites",
        "Hyatt Regency",
        "Radisson Blu Hotel",
    ],
    "meal": [
        "Barbeque Nation Hospitality Ltd",
        "Haldiram Snacks Pvt Ltd",
        "Mainland China Restaurant",
        "Paradise Food Court",
        "Chai Point (Mountain Trail Foods)",
        "Cafe Coffee Day (Coffee Day Enterprises)",
        "Sagar Ratna Restaurant",
    ],
    "fuel": [
        "Indian Oil Corporation Ltd",
        "Bharat Petroleum Corporation Ltd",
        "Hindustan Petroleum Corporation Ltd",
        "Shell India Markets Pvt Ltd",
        "Nayara Energy Ltd",
    ],
    "toll": [
        "NHAI Toll Plaza - Khed Shivapur",
        "NHAI Toll Plaza - Electronic City",
        "MEPL Mumbai Entry Points Ltd",
        "Delhi-Noida Direct (DND) Toll Plaza",
    ],
    "broadband": [
        "Bharti Airtel Ltd (Airtel Xstream)",
        "Reliance Jio Infocomm Ltd (JioFiber)",
        "Atria Convergence Technologies Ltd (ACT)",
        "Tata Play Broadband Pvt Ltd",
        "Hathway Cable and Datacom Ltd",
    ],
}

LINE_ITEMS_BY_CATEGORY = {
    "cab": ["Trip Fare", "Airport Toll Surcharge", "Convenience Fee", "Driver Tip"],
    "flight": [
        "Airfare Basic",
        "Fuel Surcharge (YQ)",
        "User Development Fee",
        "Convenience Fee",
    ],
    "hotel": [
        "Deluxe Room (1 Night)",
        "Room Service - Dinner",
        "Breakfast Buffet",
        "Laundry Service",
    ],
    "meal": [
        "Veg Buffet x1",
        "Non-Veg Buffet x1",
        "Beverages & Fresh Juice",
        "Dessert Platter",
    ],
    "fuel": [
        "Motor Spirit (Petrol) 15L",
        "High Speed Diesel 25L",
        "Engine Oil Top-up",
    ],
    "toll": [
        "Single Journey Car/Jeep Toll",
        "Return Journey Car Toll",
    ],
    "broadband": [
        "Fiber Broadband 300 Mbps Monthly",
        "Static IP Add-on",
        "Equipment Rental Charge",
    ],
}


@dataclass
class LineItem:
    description: str
    amount_paise: int


@dataclass
class ReceiptRecord:
    doc_id: str
    file: str
    doc_type: str
    vendor: str
    date: str  # YYYY-MM-DD
    total_paise: int
    taxable_paise: int
    cgst_paise: int
    sgst_paise: int
    igst_paise: int
    gstin: str
    city: str
    # Tamper types: edited_total, edited_date, pdf_resaved_with_editor,
    # screenshot, exact_duplicate, near_duplicate, or none
    tamper_type: str = "none"
    duplicate_of: str = ""
    line_items: List[LineItem] = field(default_factory=list)
    invoice_no: str = ""


def create_synthetic_receipt_record(
    doc_id: str,
    doc_type: str,
    city: Optional[str] = None,
    expense_date: Optional[str] = None,
    tamper_type: str = "none",
    duplicate_of: str = "",
    rng: Optional[random.Random] = None,
) -> ReceiptRecord:
    """Create a consistent synthetic receipt metadata record with valid GSTIN and arithmetic."""
    r = rng or random.Random()
    if doc_type not in CATEGORIES:
        doc_type = r.choice(CATEGORIES)

    selected_city = city or r.choice(CITIES)
    vendor = r.choice(VENDORS_BY_CATEGORY[doc_type])
    gstin = generate_synthetic_gstin(city=selected_city, rng=r)

    if not expense_date:
        today = datetime.date(2026, 10, 10)
        days_ago = r.randint(1, 45)
        expense_date = (today - datetime.timedelta(days=days_ago)).isoformat()

    # Generate line items
    item_candidates = LINE_ITEMS_BY_CATEGORY[doc_type]
    num_items = r.randint(1, min(3, len(item_candidates)))
    selected_items = r.sample(item_candidates, k=num_items)

    line_items: List[LineItem] = []
    base_taxable = 0
    for desc in selected_items:
        # Amount in paise (between 50.00 and 3500.00 Rs per item)
        amt = r.randint(50, 3500) * 100
        line_items.append(LineItem(description=desc, amount_paise=amt))
        base_taxable += amt

    # GST rate selection
    if doc_type == "toll":
        tax_rate = 0
    elif doc_type in ("cab", "meal"):
        tax_rate = 5
    elif doc_type in ("flight", "fuel"):
        tax_rate = 12
    else:  # hotel, broadband
        tax_rate = 18

    # Calculate GST
    is_inter_state = r.choice([True, False]) and doc_type in ("flight", "hotel")
    if tax_rate == 0:
        cgst = 0
        sgst = 0
        igst = 0
    elif is_inter_state:
        igst = (base_taxable * tax_rate) // 100
        cgst = 0
        sgst = 0
    else:
        half_rate = tax_rate // 2
        cgst = (base_taxable * half_rate) // 100
        sgst = cgst
        igst = 0

    total_paise = base_taxable + cgst + sgst + igst

    # Format invoice number
    inv_prefix = doc_type[:3].upper()
    inv_num = f"{inv_prefix}/{r.randint(10, 99)}/{r.randint(1000, 9999)}"

    # File format is determined later (e.g. .pdf or .png)
    file_ext = "pdf" if doc_type in ("flight", "broadband", "hotel") and r.random() < 0.6 else "png"
    file_name = f"{doc_id}_{doc_type}.{file_ext}"

    return ReceiptRecord(
        doc_id=doc_id,
        file=file_name,
        doc_type=doc_type,
        vendor=vendor,
        date=expense_date,
        total_paise=total_paise,
        taxable_paise=base_taxable,
        cgst_paise=cgst,
        sgst_paise=sgst,
        igst_paise=igst,
        gstin=gstin,
        city=selected_city,
        tamper_type=tamper_type,
        duplicate_of=duplicate_of,
        line_items=line_items,
        invoice_no=inv_num,
    )
