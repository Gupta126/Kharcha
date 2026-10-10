from sqlalchemy import Column, Integer, BigInteger, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, BaseModel


class Document(Base, BaseModel):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"))
    sha256 = Column(String(64), nullable=False)
    phash = Column(BigInteger)
    fuzzy_key = Column(Text)
    mime = Column(Text, nullable=False)
    pages = Column(Integer, nullable=False, default=1)
    capture_source = Column(Text, nullable=False)
    storage_uri = Column(Text)
    trust_score = Column(Integer)  # SmallInt in DB
    device_tier = Column(String(1))  # Char(1) in DB
    prompt_version = Column(Text)

    # Relationships
    employee = relationship("Employee", back_populates="documents")
    claim = relationship("Claim", back_populates="documents")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")

    # Table constraints
    __table_args__ = (
        # Unique constraint: (employee_id, sha256)
        # Will be created in migration
        # Indexes on fuzzy_key and phash will be created in migration
    )
