from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, BaseModel


class Flag(Base, BaseModel):
    __tablename__ = "flags"

    id = Column(UUID(as_uuid=True), primary_key=True)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    line_id = Column(UUID(as_uuid=True), ForeignKey("expense_lines.id"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    # type will be handled as ENUM in DB
    # severity will be handled as ENUM in DB
    rule_id = Column(Text)
    policy_version = Column(Integer)
    message = Column(Text, nullable=False)
    # evidence will be stored as JSON text
    evidence = Column(Text, nullable=False, default='{}')
    # status will be handled with default 'open' in DB
    resolution_note = Column(Text)

    # Relationships
    claim = relationship("Claim", back_populates="flags")
    line = relationship("ExpenseLine")
    document = relationship("Document")

    # Table constraints
    __table_args__ = (
        # Check constraints for type and severity will be created in migration
    )
