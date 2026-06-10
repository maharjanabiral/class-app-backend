# from sqlalchemy import Column, Integer, String, ForeignKey
# from sqlalchemy.orm import relationship
#
# from app.database import Base
#
#
# class Course(Base):
#     __tablename__ = "courses"
#
#     id = Column(Integer, primary_key=True)
#
#     course_code = Column(
#         String(50),
#         unique=True,
#         nullable=False
#     )
#
#     course_name = Column(
#         String(150),
#         nullable=False
#     )
#
#     class_id = Column(
#         Integer,
#         ForeignKey("classes.id")
#     )
#
#     teacher_id = Column(
#         Integer,
#         ForeignKey("teachers.id")
#     )
#
#     classroom = relationship(
#         "Classroom",
#         back_populates="courses"
#     )
#
#     teacher = relationship(
#         "Teacher",
#         back_populates="courses"
#     )
