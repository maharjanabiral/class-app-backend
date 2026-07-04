from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True)
    session_id = Column(
        Integer,
        ForeignKey("class_sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False
    )
    marked_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ClassSession", back_populates="attendance_records")
    student = relationship("Student")

    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_session_student"),
    )
