from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel


class Claim(Base, BaseModel):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    title = Column(Text)
    trip_start = Column(Date)
    trip_end = Column(Date)
    city = Column(Text)
    # status will be handled as ENUM in DB
    total_paise = Column(BigInteger, nullable=False, default=0)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"))
    erp_ref = Column(Text)
    submitted_at = Column(DateTime(timezone=True))
    decided_at = Column(DateTime(timezone=True))

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="claims")
    approver = relationship("Employee", foreign_keys=[approver_id])
    expense_lines = relationship(
        "ExpenseLine", back_populates="claim", cascade="all, delete-orphan"
    )
    documents = relationship("Document", back_populates="claim")
    flags = relationship("Flag", back_populates="claim")
    questions = relationship("Question", back_populates="claim")
    agent_messages = relationship("AgentMessage", back_populates="claim")
    llm_calls = relationship("LLMCall", back_populates="claim")
    audit_events = relationship("AuditEvent", back_populates="claim")

    # Indexes
    __table_args__ = (
        # Index on (employee_id, status)
        # Will be created in migration
    )
