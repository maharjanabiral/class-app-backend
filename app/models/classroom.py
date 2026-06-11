from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True)

    name = Column(String(100), nullable=False)

    students = relationship(
        "Student",
        back_populates="classroom"
    )

    class_courses = relationship("ClassCourse", back_populates="classroom")
