from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class AuditEvent(Base, BaseModel):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True)
    actor_id = Column(UUID(as_uuid=True))
    action = Column(Text, nullable=False)
    target_type = Column(Text, nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    # before and after will be stored as JSON text
    before = Column(Text)
    after = Column(Text)
    at = Column(DateTime(timezone=True), nullable=False, server_default="now()")

    # Relationships
    claim = relationship("Claim", back_populates="audit_events")

    # Table constraints
    __table_args__ = (
        # No additional constraints needed
    )
