from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)

    class_course_id = Column(
        Integer,
        ForeignKey("class_courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    class_course = relationship(
        "ClassCourse",
        back_populates="notes"
    )
