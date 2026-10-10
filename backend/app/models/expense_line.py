import uuid
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.claim import Claim
from sqlalchemy import BigInteger, Date, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel


class ExpenseLine(Base, BaseModel):
    __tablename__ = "expense_lines"

    __table_args__ = (Index("ix_expense_lines_claim_id", "claim_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id")
    )
    category: Mapped[str] = mapped_column(
        ENUM(
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
            name="expense_category",
            create_type=False,
        ),
        nullable=False,
    )
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    vendor: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    claimable_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cgst_paise: Mapped[int | None] = mapped_column(BigInteger)
    sgst_paise: Mapped[int | None] = mapped_column(BigInteger)
    igst_paise: Mapped[int | None] = mapped_column(BigInteger)
    gstin: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    attendees: Mapped[str] = mapped_column(Text, server_default="'[]'", nullable=False)
    excluded_reason: Mapped[str | None] = mapped_column(Text)

    claim: Mapped["Claim"] = relationship("Claim", back_populates="expense_lines")
