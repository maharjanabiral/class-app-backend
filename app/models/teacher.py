from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Integer, func
from sqlalchemy.orm import relationship
from app.database import Base


class Teacher(Base):

    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True)
    teacher_id = Column(String(20), unique=True, index=False, nullable=False)
    user_id = Column(
                Integer,
                ForeignKey("users.id", ondelete="CASCADE"),
                unique=True,
                nullable=False
            )

    phone = Column(String(10))
    department = Column(String(20))
    user = relationship("User", back_populates="teacher")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


