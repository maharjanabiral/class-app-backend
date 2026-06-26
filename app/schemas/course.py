from pydantic import BaseModel
from typing import Optional
from app.schemas.attendance import CourseSessionStats


class CourseCreate(BaseModel):
    course_code: str
    course_name: str


class CourseUpdate(BaseModel):
    course_name: Optional[str] = None
    course_code: Optional[str] = None


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


class TeacherCourseDetailResponse(BaseModel):
    id: int
    course_code: str
    course_name: str

    classroom_id: int
    classroom_name: str

    total_sessions: int

    active_session: Optional[CourseSessionStats]
    # recent_sessions: list[CourseSessionStats]
    all_sessions: list[CourseSessionStats]

    class Config:
        from_attributes = True
