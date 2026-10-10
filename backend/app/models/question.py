from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, BaseModel


class Question(Base, BaseModel):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    line_id = Column(UUID(as_uuid=True), ForeignKey("expense_lines.id"))
    field = Column(Text, nullable=False)
    prompt = Column(Text, nullable=False)
    # options will be stored as JSON text
    options = Column(Text, nullable=False, default='[]')
    # answer will be stored as JSON text
    answer = Column(Text)
    asked_at = Column(DateTime(timezone=True), nullable=False, server_default='now()')
    answered_at = Column(DateTime(timezone=True))

    # Relationships
    claim = relationship("Claim", back_populates="questions")
    line = relationship("ExpenseLine")

    # Table constraints
    __table_args__ = (
        # No additional constraints needed
    )
