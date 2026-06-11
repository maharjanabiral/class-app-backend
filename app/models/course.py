from sqlalchemy import Column, Integer, String
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

    class_courses = relationship("ClassCourse", back_populates="course")
