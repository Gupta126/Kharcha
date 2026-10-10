from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base, BaseModel


class Employee(Base, BaseModel):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    grade = Column(String(50), nullable=False)
    cost_centre = Column(String(100))
    home_city = Column(String(100))
    manager_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"))
    role = Column(String(50), nullable=False, default="employee")

    # Relationships
    manager = relationship("Employee", remote_side=[id], backref="subordinates")
    entitlements = relationship("Entitlement", back_populates="employee")
    claims = relationship("Claim", back_populates="employee")
    documents = relationship("Document", back_populates="employee")
