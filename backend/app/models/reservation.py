from sqlalchemy import BigInteger, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class Reservation(Base, BaseModel):
    __tablename__ = "reservations"

    id = Column(UUID(as_uuid=True), primary_key=True)
    entitlement_id = Column(UUID(as_uuid=True), ForeignKey("entitlements.id"), nullable=False)
    line_id = Column(UUID(as_uuid=True), ForeignKey("expense_lines.id"), nullable=False)
    amount_paise = Column(BigInteger, nullable=False)
    # status will be handled as CHECK constraint in DB: ('held','released','consumed')

    # Relationships
    entitlement = relationship("Entitlement")
    line = relationship("ExpenseLine", back_populates="reservations")

    # Table constraints
    __table_args__ = (
        # Check constraint for status will be created in migration
        # Index on entitlement_id will be created in migration
    )
