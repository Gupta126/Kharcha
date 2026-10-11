"""Tamper application and artifact injection for synthetic receipts."""

import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from data.generator.models import ReceiptRecord
from data.generator.renderer import (
    get_default_font,
    render_receipt_image,
    render_receipt_pdf,
)

PDF_EDITORS = [
    ("Adobe Acrobat Pro DC 2024", "Adobe PDF Library 24.1"),
    ("Canva Editor PDF Export", "Canva Pro Engine"),
    ("PDF-XChange Editor v10.0", "Tracker Software Products"),
    ("Nitro Pro 14.12", "Nitro Software, Inc."),
]


def add_screenshot_frame(img: Image.Image, rng: random.Random) -> Image.Image:
    """Wrap a receipt image inside a mobile screenshot frame with status bar."""
    status_bar_h = 36
    nav_bar_h = 24
    margin = 12

    new_w = img.width + (margin * 2)
    new_h = img.height + status_bar_h + nav_bar_h + (margin * 2)

    # Smartphone canvas background
    canvas_img = Image.new("RGB", (new_w, new_h), (18, 18, 20))
    draw = ImageDraw.Draw(canvas_img)

    # Paste receipt image in center
    canvas_img.paste(img, (margin, status_bar_h + margin))

    font = get_default_font(12)
    time_str = f"{rng.randint(9, 21):02d}:{rng.randint(10, 59):02d}"

    # Draw status bar at top (clock, icons)
    draw.text((margin + 10, 10), time_str, fill=(240, 240, 240), font=font)
    draw.text((new_w - margin - 85, 10), "5G  87%", fill=(240, 240, 240), font=font)

    # Draw battery indicator rectangle
    draw.rectangle(
        [(new_w - margin - 25, 12), (new_w - margin - 10, 24)],
        outline=(240, 240, 240),
        width=1,
    )
    draw.rectangle([(new_w - margin - 23, 14), (new_w - margin - 13, 22)], fill=(240, 240, 240))

    # Draw home navigation bar line at bottom
    bar_w = 120
    bar_x = (new_w - bar_w) // 2
    bar_y = new_h - 14
    draw.line([(bar_x, bar_y), (bar_x + bar_w, bar_y)], fill=(200, 200, 200), width=3)

    return canvas_img


def render_tampered_document(
    record: ReceiptRecord,
    output_dir: Path,
    original_target_record: ReceiptRecord | None = None,
    rng: random.Random | None = None,
) -> None:
    """Render a document according to its tamper type and write it to output_dir."""
    r = rng or random.Random()
    out_file = output_dir / record.file
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ttype = record.tamper_type

    if ttype == "exact_duplicate":
        if not original_target_record:
            raise ValueError("exact_duplicate requires original_target_record")
        orig_file = output_dir / original_target_record.file
        shutil.copy2(orig_file, out_file)
        return

    if ttype == "near_duplicate":
        if not original_target_record:
            raise ValueError("near_duplicate requires original_target_record")
        # Re-render the same transaction with different visual angle / crop / noise
        if record.file.endswith(".pdf"):
            render_receipt_pdf(record, out_file)
        else:
            img = render_receipt_image(record, add_artifacts=True, rng=r)
            # Apply distinct subtle rotation/crop
            img = img.rotate(r.uniform(1.0, 3.5), expand=True, fillcolor=(255, 255, 255))
            img.save(out_file, format="PNG")
        return

    if ttype == "pdf_resaved_with_editor":
        # Must be PDF with editor metadata
        editor, producer = r.choice(PDF_EDITORS)
        render_receipt_pdf(record, out_file, producer=producer, creator=editor)
        return

    if ttype == "edited_total":
        # Inflate the displayed total on the visual document by ₹500 - ₹2000
        inflated_total = record.total_paise + r.randint(500, 2000) * 100
        if record.file.endswith(".pdf"):
            render_receipt_pdf(record, out_file, display_total_override=inflated_total)
        else:
            img = render_receipt_image(record, display_total_override=inflated_total, rng=r)
            img.save(out_file, format="PNG")
        return

    if ttype == "edited_date":
        # Change date shown on the document to a different date
        altered_date = "2025-01-15"
        if record.file.endswith(".pdf"):
            render_receipt_pdf(record, out_file, display_date_override=altered_date)
        else:
            img = render_receipt_image(record, display_date_override=altered_date, rng=r)
            img.save(out_file, format="PNG")
        return

    if ttype == "screenshot":
        # Must be image format wrapped in screenshot frame
        img = render_receipt_image(record, add_artifacts=False, rng=r)
        screen_img = add_screenshot_frame(img, rng=r)
        screen_img.save(out_file, format="PNG")
        return

    # Default / untampered ("none")
    if record.file.endswith(".pdf"):
        render_receipt_pdf(record, out_file)
    else:
        img = render_receipt_image(record, add_artifacts=True, rng=r)
        img.save(out_file, format="PNG")
