import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BaseModel


class Document(Base, BaseModel):
    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint("employee_id", "sha256"),
        Index("ix_documents_fuzzy_key", "fuzzy_key"),
        Index("ix_documents_phash", "phash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False
    )
    claim_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("claims.id"))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    phash: Mapped[int | None] = mapped_column(BigInteger)
    fuzzy_key: Mapped[str | None] = mapped_column(Text)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    pages: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    capture_source: Mapped[str] = mapped_column(Text, nullable=False)
    storage_uri: Mapped[str | None] = mapped_column(Text)
    trust_score: Mapped[int | None] = mapped_column(Integer)
    device_tier: Mapped[str | None] = mapped_column(String(1))
    prompt_version: Mapped[str | None] = mapped_column(Text)
