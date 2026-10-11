"""Pure-Python rendering of receipts into PNG images and PDF documents."""

import random
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from data.generator.models import ReceiptRecord


def format_inr(paise: int) -> str:
    """Format paise as INR string (e.g. 150000 -> '1,500.00')."""
    rupees = paise / 100.0
    return f"{rupees:,.2f}"


def get_default_font(size: int = 14) -> ImageFont.ImageFont:
    """Load default PIL font or fallback."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def render_receipt_image(
    record: ReceiptRecord,
    add_artifacts: bool = True,
    display_total_override: Optional[int] = None,
    display_date_override: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> Image.Image:
    """Render a realistic receipt as a PIL Image with optional tilt/blur/folds."""
    r = rng or random.Random()
    width = 480
    height = 680

    # Off-white / thermal receipt background
    bg_color = (r.randint(248, 255), r.randint(248, 255), r.randint(242, 250))
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    text_color = (30, 30, 30)
    gray_color = (110, 110, 110)

    font_title = get_default_font(18)
    font_bold = get_default_font(15)
    font_reg = get_default_font(13)
    font_small = get_default_font(11)

    y = 25

    # Header / Vendor Name
    draw.text((width // 2, y), record.vendor, fill=text_color, font=font_title, anchor="mt")
    y += 28
    draw.text(
        (width // 2, y),
        f"City: {record.city} | GSTIN: {record.gstin}",
        fill=gray_color,
        font=font_small,
        anchor="mt",
    )
    y += 20
    draw.line([(25, y), (width - 25, y)], fill=(180, 180, 180), width=1)
    y += 15

    # Invoice metadata
    date_str = display_date_override if display_date_override is not None else record.date
    draw.text((25, y), f"Date: {date_str}", fill=text_color, font=font_reg)
    draw.text(
        (width - 25, y), f"Inv: {record.invoice_no}", fill=text_color, font=font_reg, anchor="ra"
    )
    y += 22
    draw.text((25, y), f"Type: {record.doc_type.upper()}", fill=gray_color, font=font_small)
    draw.text(
        (width - 25, y), f"ID: {record.doc_id}", fill=gray_color, font=font_small, anchor="ra"
    )
    y += 25
    draw.line([(25, y), (width - 25, y)], fill=(180, 180, 180), width=1)
    y += 15

    # Column Headers
    draw.text((25, y), "ITEM DESCRIPTION", fill=text_color, font=font_bold)
    draw.text((width - 25, y), "AMOUNT (INR)", fill=text_color, font=font_bold, anchor="ra")
    y += 22
    draw.line([(25, y), (width - 25, y)], fill=(200, 200, 200), width=1)
    y += 12

    # Line Items
    for item in record.line_items:
        draw.text((25, y), item.description, fill=text_color, font=font_reg)
        formatted_item_amt = format_inr(item.amount_paise)
        draw.text((width - 25, y), formatted_item_amt, fill=text_color, font=font_reg, anchor="ra")
        y += 22

    y += 10
    draw.line([(25, y), (width - 25, y)], fill=(180, 180, 180), width=1)
    y += 15

    # Tax breakdown
    draw.text((25, y), "Taxable Amount:", fill=gray_color, font=font_reg)
    draw.text(
        (width - 25, y),
        format_inr(record.taxable_paise),
        fill=text_color,
        font=font_reg,
        anchor="ra",
    )
    y += 20

    if record.cgst_paise > 0:
        draw.text((25, y), "CGST:", fill=gray_color, font=font_reg)
        draw.text(
            (width - 25, y),
            format_inr(record.cgst_paise),
            fill=text_color,
            font=font_reg,
            anchor="ra",
        )
        y += 20
    if record.sgst_paise > 0:
        draw.text((25, y), "SGST:", fill=gray_color, font=font_reg)
        draw.text(
            (width - 25, y),
            format_inr(record.sgst_paise),
            fill=text_color,
            font=font_reg,
            anchor="ra",
        )
        y += 20
    if record.igst_paise > 0:
        draw.text((25, y), "IGST:", fill=gray_color, font=font_reg)
        draw.text(
            (width - 25, y),
            format_inr(record.igst_paise),
            fill=text_color,
            font=font_reg,
            anchor="ra",
        )
        y += 20

    y += 5
    draw.line([(25, y), (width - 25, y)], fill=(80, 80, 80), width=2)
    y += 15

    # Total Amount
    if display_total_override is not None:
        total_to_display = display_total_override
    else:
        total_to_display = record.total_paise

    draw.text((25, y), "TOTAL:", fill=text_color, font=font_bold)
    draw.text(
        (width - 25, y),
        f"INR {format_inr(total_to_display)}",
        fill=(0, 0, 120),
        font=font_bold,
        anchor="ra",
    )
    y += 35

    # Footer
    draw.line([(25, y), (width - 25, y)], fill=(200, 200, 200), width=1)
    y += 15
    draw.text(
        (width // 2, y),
        "Payment: Confirmed (UPI / Card)",
        fill=gray_color,
        font=font_small,
        anchor="mt",
    )
    y += 18
    draw.text(
        (width // 2, y),
        "*** Thank you for your business! ***",
        fill=gray_color,
        font=font_small,
        anchor="mt",
    )

    if not add_artifacts:
        return img

    # Add realistic receipt artifacts:
    # 1. Subtle horizontal / diagonal fold creases
    fold_y = r.randint(180, 420)
    draw.line([(0, fold_y), (width, fold_y + r.randint(-10, 10))], fill=(225, 225, 220), width=2)

    # 2. Slight rotation / tilt (-2.5 to 2.5 degrees)
    angle = r.uniform(-2.5, 2.5)
    img = img.rotate(
        angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(255, 255, 255)
    )

    # 3. Slight blur / defocus
    if r.random() < 0.4:
        img = img.filter(ImageFilter.GaussianBlur(radius=r.uniform(0.3, 0.8)))

    return img


def render_receipt_pdf(
    record: ReceiptRecord,
    output_path: Path,
    producer: Optional[str] = None,
    creator: Optional[str] = None,
    display_total_override: Optional[int] = None,
    display_date_override: Optional[str] = None,
) -> None:
    """Render a structured PDF invoice using ReportLab."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=letter)
    page_w, page_h = letter

    # Metadata
    if producer:
        c.setProducer(producer)
    else:
        c.setProducer("ReportLab PDF Library")

    if creator:
        c.setCreator(creator)
    else:
        c.setCreator("Kharcha Invoicing System v1.0")

    c.setTitle(f"Invoice - {record.invoice_no}")

    # Draw header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, page_h - 60, record.vendor)

    c.setFont("Helvetica", 10)
    c.drawString(50, page_h - 78, f"City: {record.city} | GSTIN: {record.gstin}")
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(1)
    c.line(50, page_h - 90, page_w - 50, page_h - 90)

    # Metadata
    c.setFont("Helvetica", 11)
    date_str = display_date_override if display_date_override is not None else record.date
    c.drawString(50, page_h - 110, f"Invoice No: {record.invoice_no}")
    c.drawRightString(page_w - 50, page_h - 110, f"Date: {date_str}")
    c.drawString(50, page_h - 128, f"Category: {record.doc_type.upper()}")
    c.drawRightString(page_w - 50, page_h - 128, f"Doc ID: {record.doc_id}")

    c.line(50, page_h - 140, page_w - 50, page_h - 140)

    # Table header
    y = page_h - 165
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Item Description")
    c.drawRightString(page_w - 50, y, "Amount (INR)")
    y -= 10
    c.line(50, y, page_w - 50, y)
    y -= 20

    # Line items
    c.setFont("Helvetica", 11)
    for item in record.line_items:
        c.drawString(50, y, item.description)
        c.drawRightString(page_w - 50, y, format_inr(item.amount_paise))
        y -= 22

    y -= 10
    c.line(50, y, page_w - 50, y)
    y -= 20

    # Subtotals & Taxes
    c.drawString(50, y, "Taxable Subtotal:")
    c.drawRightString(page_w - 50, y, format_inr(record.taxable_paise))
    y -= 18

    if record.cgst_paise > 0:
        c.drawString(50, y, "CGST:")
        c.drawRightString(page_w - 50, y, format_inr(record.cgst_paise))
        y -= 18
    if record.sgst_paise > 0:
        c.drawString(50, y, "SGST:")
        c.drawRightString(page_w - 50, y, format_inr(record.sgst_paise))
        y -= 18
    if record.igst_paise > 0:
        c.drawString(50, y, "IGST:")
        c.drawRightString(page_w - 50, y, format_inr(record.igst_paise))
        y -= 18

    c.setLineWidth(2)
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.line(50, y, page_w - 50, y)
    y -= 22

    # Total
    total_val = display_total_override if display_total_override is not None else record.total_paise
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "Total Invoice Amount:")
    c.drawRightString(page_w - 50, y, f"INR {format_inr(total_val)}")

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(page_w / 2.0, 50, "Computer generated invoice. No signature required.")

    c.showPage()
    c.save()
