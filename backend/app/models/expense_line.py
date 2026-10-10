from sqlalchemy import Column, Date, BigInteger, Enum, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, BaseModel


class ExpenseLine(Base, BaseModel):
    __tablename__ = "expense_lines"

    id = Column(UUID(as_uuid=True), primary_key=True)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    # category will be handled as ENUM in DB
    expense_date = Column(Date, nullable=False)
    vendor = Column(Text)
    city = Column(Text)
    amount_paise = Column(BigInteger, nullable=False)
    claimable_paise = Column(BigInteger, nullable=False)
    cgst_paise = Column(BigInteger)
    sgst_paise = Column(BigInteger)
    igst_paise = Column(BigInteger)
    gstin = Column(Text)
    purpose = Column(Text)
    # attendees will be stored as JSON text
    attendees = Column(Text, nullable=False, default='[]')
    excluded_reason = Column(Text)

    # Relationships
    claim = relationship("Claim", back_populates="expense_lines")
    document = relationship("Document")
    reservations = relationship("Reservation", back_populates="line", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="expense_line")

    # Indexes
    __table_args__ = (
        # Index on claim_id
        # Will be created in migration
    )
