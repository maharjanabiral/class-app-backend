from sqlalchemy import Boolean, Column, Integer, String, Enum, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class Role(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(Role), nullable=False)
    is_active = Column(Boolean, default=True)

    login_id = Column(String(50), unique=True, index=True, nullable=True)
    is_created_by_admin = Column(Boolean, default=False)
    remember_token = Column(String(50), nullable=True, index=True)
    remember_token_expiry = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship(
                "Student",
                back_populates="user",
                uselist=False,
                cascade="all, delete-orphan"
            )

    teacher = relationship(
                "Teacher",
                back_populates="user",
                uselist=False,
                cascade="all, delete-orphan"
            )
