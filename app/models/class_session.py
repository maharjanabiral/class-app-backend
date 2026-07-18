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

    room_name = Column()

    # --- Live meeting fields ---
    room_name = Column(String, nullable=True, unique=True)
    room_status = Column(String, default="not_started", nullable=False)
    # not_started | live | ended
    recording_url = Column(String, nullable=True)
    recording_status = Column(String, nullable=True)

    course = relationship("Course", back_populates="sessions")
    attendance_records = relationship(
        "AttendanceRecord",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    participants = relationship("SessionParticipant", back_populates="session", cascade="all, delete-orphan")
