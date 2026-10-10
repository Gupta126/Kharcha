import uuid

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseModel

flag_type_enum = ENUM(
    "policy",
    "entitlement",
    "duplicate",
    "authenticity",
    "missing",
    name="flag_type",
    create_type=False,
)
severity_enum = ENUM("green", "amber", "red", name="severity", create_type=False)


class Flag(Base, BaseModel):
    __tablename__ = "flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_lines.id")
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id")
    )
    type: Mapped[str] = mapped_column(flag_type_enum, nullable=False)
    severity: Mapped[str] = mapped_column(severity_enum, nullable=False)
    rule_id: Mapped[str | None] = mapped_column(Text)
    policy_version: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, server_default="'{}'", nullable=False)
    status: Mapped[str] = mapped_column(Text, server_default="'open'", nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text)
