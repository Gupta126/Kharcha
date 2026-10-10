from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class AgentMessage(Base, BaseModel):
    __tablename__ = "agent_messages"

    id = Column(UUID(as_uuid=True), primary_key=True)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    # role will be stored as text (could be ENUM but keeping simple)
    role = Column(Text, nullable=False)
    # content will be stored as JSON text
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    claim = relationship("Claim", back_populates="agent_messages")

    # Table constraints
    __table_args__ = (
        # No additional constraints needed
    )
