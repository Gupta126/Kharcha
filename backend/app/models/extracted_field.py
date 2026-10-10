from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class ExtractedField(Base, BaseModel):
    __tablename__ = "extracted_fields"

    id = Column(UUID(as_uuid=True), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    name = Column(Text, nullable=False)
    # value will be stored as JSON text
    value = Column(Text, nullable=False)
    confidence = Column(Integer)  # Real in DB
    # bbox will be stored as array of integers
    bbox = Column(Text)  # We'll handle this as text or provide a custom type
    source = Column(Text, nullable=False)  # Will be handled as ENUM in DB

    # Relationships
    document = relationship("Document", back_populates="extracted_fields")
    expense_line = relationship("ExpenseLine", back_populates="extracted_fields")

    # Table constraints
    __table_args__ = (
        # Check constraint for source will be created in migration
    )
