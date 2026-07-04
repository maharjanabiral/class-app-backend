from pydantic import BaseModel
from typing import Optional, List


class ClassroomCreate(BaseModel):
    name: str
    section: Optional[str] = None
    academic_year: str


class ClassroomUpdate(BaseModel):
    name: Optional[str] = None
    section: Optional[str] = None
    academic_year: Optional[str] = None


class ClassroomResponse(BaseModel):
    id: int
    name: str
    section: str | None
    academic_year: str

    class Config:
        from_attributes = True


class EnrollStudentRequest(BaseModel):
    student_id: str  # the STU001 login_id


class EnrollStudentWithRollRequest(BaseModel):
    student_id: str   # the STU001 login_id
    roll_no: Optional[str] = None


class AssignCourseRequest(BaseModel):
    course_id: int
    teacher_id: Optional[int] = None


class StudentInClassroom(BaseModel):
    id: int
    student_id: str
    roll_no: Optional[str] = None
    name: str
    email: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class CourseInClassroom(BaseModel):
    id: int
    course_code: str
    course_name: str
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class ClassroomDetail(BaseModel):
    id: int
    name: str
    section: Optional[str] = None
    academic_year: str
    students: List[StudentInClassroom] = []
    courses: List[CourseInClassroom] = []

    class Config:
        from_attributes = True
