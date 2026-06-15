from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.database import Base


course_students = Table(
    "course_students",
    Base.metadata,
    Column("course_id", Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
)


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
        ForeignKey("classrooms.id")
    )

    teacher_id = Column(
        Integer,
        ForeignKey("teachers.id")
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

    students = relationship(
        "Student",
        secondary=course_students,
        back_populates="courses"
    )
