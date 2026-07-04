from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)

    course_code = Column(
        String(50),
        unique=True,
        nullable=False
    )

    course_name = Column(
        String(150),
        nullable=False
    )

    classroom_id = Column(
        Integer,
        ForeignKey("classrooms.id"),
        nullable=True
    )

    teacher_id = Column(
        Integer,
        ForeignKey("teachers.id"),
        nullable=True
    )

    classroom = relationship(
        "Classroom",
        back_populates="courses"
    )

    teacher = relationship(
        "Teacher",
        back_populates="courses"
    )

    sessions = relationship(
        "ClassSession",
        back_populates="course",
        cascade="all, delete-orphan"
    )

    notes = relationship("Note", back_populates="course", cascade="all, delete")
