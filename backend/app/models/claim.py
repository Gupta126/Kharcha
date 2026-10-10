import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.expense_line import ExpenseLine
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel

claim_status_enum = ENUM(
    "draft",
    "needs_info",
    "ready",
    "submitted",
    "in_review",
    "approved",
    "rejected",
    "returned",
    "paid",
    name="claim_status",
    create_type=False,
)


class Claim(Base, BaseModel):
    __tablename__ = "claims"

    __table_args__ = (Index("ix_claims_employee_id_status", "employee_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(Text)
    trip_start: Mapped[date | None] = mapped_column(Date)
    trip_end: Mapped[date | None] = mapped_column(Date)
    city: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(claim_status_enum, server_default="draft", nullable=False)
    total_paise: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id")
    )
    erp_ref: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    employee: Mapped["Employee"] = relationship(
        "Employee", foreign_keys=[employee_id], back_populates="claims"
    )
    expense_lines: Mapped[list["ExpenseLine"]] = relationship(
        "ExpenseLine", back_populates="claim", cascade="all, delete-orphan"
    )
