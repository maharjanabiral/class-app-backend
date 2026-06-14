from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func, Enum
from app.database import Base
import enum


class TargetRole(str, enum.Enum):
    all = "all"
    teacher = "teacher"
    student = "student"


class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    target_role = Column(Enum(TargetRole), default=TargetRole.all, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
