from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)

    user_id = Column(
                Integer, 
                ForeignKey("users.id", ondelete="CASCADE"),
                unique=True,
                nullable=False
            )

    class_id = Column(
                Integer,
                ForeignKey("classes.id", ondelete="CASCADE")
            )

    roll_no = Column(String(50), unique=True)
    phone = Column(String(10))
    user = relationship("User", back_populates="student")
    classroom = relationship("Classroom", back_populates="students")
