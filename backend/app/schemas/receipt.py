"""Pydantic v2 model mirroring contracts/receipt.schema.json exactly."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VendorField(StrictBaseModel):
    value: str = Field(..., min_length=1)
    conf: float = Field(..., ge=0.0, le=1.0)
    bbox: list[int] | None = Field(None, min_length=4, max_length=4)


class DateField(StrictBaseModel):
    value: str = Field(...)
    conf: float = Field(..., ge=0.0, le=1.0)
    bbox: list[int] | None = Field(None, min_length=4, max_length=4)


class TimeField(StrictBaseModel):
    value: str = Field(..., pattern=r"^[0-2][0-9]:[0-5][0-9]$")
    conf: float = Field(..., ge=0.0, le=1.0)
    bbox: list[int] | None = Field(None, min_length=4, max_length=4)


class CityField(StrictBaseModel):
    value: str = Field(...)
    conf: float = Field(..., ge=0.0, le=1.0)
    bbox: list[int] | None = Field(None, min_length=4, max_length=4)


class TotalField(StrictBaseModel):
    value_paise: int = Field(..., ge=0)
    currency: Literal["INR"] = "INR"
    conf: float = Field(..., ge=0.0, le=1.0)


class TaxField(StrictBaseModel):
    taxable_paise: int | None = None
    cgst_paise: int | None = None
    sgst_paise: int | None = None
    igst_paise: int | None = None
    rate: float | None = None
    conf: float | None = Field(None, ge=0.0, le=1.0)


class GstinField(StrictBaseModel):
    value: str = Field(...)
    checksum_ok: bool | None = None


class InvoiceNoField(StrictBaseModel):
    value: str = Field(...)
    conf: float = Field(..., ge=0.0, le=1.0)
    bbox: list[int] | None = Field(None, min_length=4, max_length=4)


class PaymentModeField(StrictBaseModel):
    value: Literal["UPI", "card", "cash", "wallet", "bank_transfer", "unknown"]
    conf: float = Field(..., ge=0.0, le=1.0)
    bbox: list[int] | None = Field(None, min_length=4, max_length=4)


class LineItemField(StrictBaseModel):
    desc: str = Field(...)
    qty: float | None = None
    amount_paise: int = Field(...)


class TrustField(StrictBaseModel):
    score: int | None = Field(None, ge=0, le=100)
    signals: list[str] | None = None


class ExtractedReceipt(StrictBaseModel):
    doc_id: str
    doc_type: Literal[
        "flight",
        "rail",
        "cab",
        "hotel",
        "meal",
        "fuel",
        "toll",
        "telecom",
        "broadband",
        "other",
    ]
    lang: list[Literal["en", "hi"]] | None = None
    vendor: VendorField
    date: DateField
    time: TimeField | None = None
    city: CityField | None = None
    total: TotalField
    tax: TaxField | None = None
    gstin: GstinField | None = None
    invoice_no: InvoiceNoField | None = None
    payment_mode: PaymentModeField | None = None
    nights: int | None = Field(None, ge=1)
    line_items: list[LineItemField] | None = None
    trust: TrustField | None = None
    prompt_version: str | None = None
