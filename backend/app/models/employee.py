import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.claim import Claim
from app.models.base import Base, BaseModel


class Employee(Base, BaseModel):
    __tablename__ = "employees"

    __table_args__ = (
        Index("ix_employees_email", "email", unique=True),
        UniqueConstraint("email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    cost_centre: Mapped[str | None] = mapped_column(String(100))
    home_city: Mapped[str | None] = mapped_column(String(100))
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id")
    )
    role: Mapped[str] = mapped_column(String(50), server_default="'employee'", nullable=False)

    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="employee", foreign_keys="[Claim.employee_id]"
    )
