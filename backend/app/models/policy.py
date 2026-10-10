from sqlalchemy import Boolean, Column, Date, Integer, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, BaseModel


class Policy(Base, BaseModel):
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True)
    version = Column(Integer, unique=True, nullable=False)
    rules = Column(Text, nullable=False)  # Storing as JSON text
    effective_from = Column(Date, nullable=False)
    active = Column(Boolean, nullable=False, default=False)
