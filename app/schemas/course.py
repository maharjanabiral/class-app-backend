from pydantic import BaseModel


class CourseCreate(BaseModel):
    course_code: str
    course_name: str
    class_id: int
    teacher_id: int


class CourseResponse(BaseModel):
    id: int
    course_code: str
    course_name: str
    class_id: int
    teacher_id: int

    class Config:
        from_attributes = True
