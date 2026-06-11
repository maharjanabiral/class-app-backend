from pydantic import BaseModel


class ClassCourseCreate(BaseModel):
    class_id: int
    course_id: int
    teacher_id: int
