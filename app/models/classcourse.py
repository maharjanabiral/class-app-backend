from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class ClassCourse(Base):
    __tablename__ = "class_courses"

    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint(
            "class_id",
            "course_id",
            name="uq_class_course"
        ),
    )

    classroom = relationship(
        "Classroom",
        back_populates="class_courses"
    )

    course = relationship(
        "Course",
        back_populates="class_courses"
    )

    teacher = relationship(
        "Teacher",
        back_populates="class_courses"
    )

    notes = relationship(
        "Note",
        back_populates="class_course",
        cascade="all, delete-orphan"
    )
