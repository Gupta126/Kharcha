from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class Entitlement(Base, BaseModel):
    __tablename__ = "entitlements"

    id = Column(UUID(as_uuid=True), primary_key=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    category = Column(Text)  # Will be handled as ENUM in DB, stored as text in model
    overall = Column(Boolean, nullable=False, default=False)
    period = Column(Text)  # Will be handled as ENUM in DB, stored as text in model
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    limit_paise = Column(BigInteger, nullable=False)
    paid_paise = Column(BigInteger, nullable=False, default=0)
    fetched_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="entitlements")

    # Table constraints
    __table_args__ = (
        # Unique constraint: (employee_id, category, period_start)
        # Note: In practice, we'd use the actual ENUM types, but for SQLAlchemy portability
        # we'll handle this at the database level through the migration
    )
