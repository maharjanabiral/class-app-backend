from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Classroom(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)

    name = Column(String(100), nullable=False)

    section = Column(String(20), nullable=True)

    academic_year = Column(String(20), nullable=False)

    students = relationship(
        "Student",
        back_populates="classroom"
    )

    courses = relationship(
        "Course",
        back_populates="classroom"
    )
