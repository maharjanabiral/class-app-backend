from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id = Column(Integer, primary_key=True)
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )
    title = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="sessions")
    attendance_records = relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    participants = relationship("SessionParticipant", back_populates="session", cascade="all, delete-orphan")
