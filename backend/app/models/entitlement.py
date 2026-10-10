import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseModel


class Entitlement(Base, BaseModel):
    __tablename__ = "entitlements"

    __table_args__ = (UniqueConstraint("employee_id", "category", "period_start"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    overall: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    period: Mapped[str] = mapped_column(
        ENUM("month", "quarter", "fin_year", "per_trip", name="period_kind", create_type=False),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    limit_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_paise: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
