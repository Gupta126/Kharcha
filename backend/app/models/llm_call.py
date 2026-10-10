from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, BaseModel


class LLMCall(Base, BaseModel):
    __tablename__ = "llm_calls"

    id = Column(UUID(as_uuid=True), primary_key=True)
    task = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    model = Column(Text, nullable=False)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    latency_ms = Column(Integer)
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    success = Column(Integer)  # Boolean in DB (0/1)
    failure = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default='now()')

    # Relationships
    claim = relationship("Claim", back_populates="llm_calls")
    document = relationship("Document")

    # Table constraints
    __table_args__ = (
        # No additional constraints needed
    )
