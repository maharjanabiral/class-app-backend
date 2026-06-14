from pydantic import BaseModel
from typing import Optional


class CourseCreate(BaseModel):
    course_code: str
    course_name: str
    class_id: int
    teacher_id: Optional[int] = None  # internal DB id of teacher


class CourseUpdate(BaseModel):
    course_name: Optional[str] = None
    class_id: Optional[int] = None
    teacher_id: Optional[int] = None


class TeacherBrief(BaseModel):
    id: int
    teacher_id: str
    name: str

    class Config:
        from_attributes = True


class ClassroomBrief(BaseModel):
    id: int
    name: str
    section: Optional[str] = None
    academic_year: str

    class Config:
        from_attributes = True


class CourseResponse(BaseModel):
    id: int
    course_code: str
    course_name: str
    class_id: Optional[int] = None
    teacher_id: Optional[int] = None

    class Config:
        from_attributes = True


class CourseDetailResponse(BaseModel):
    id: int
    course_code: str
    course_name: str
    classroom: Optional[ClassroomBrief] = None
    teacher: Optional[TeacherBrief] = None

    class Config:
        from_attributes = True
