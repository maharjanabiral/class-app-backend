from datetime import datetime
from pydantic import BaseModel


class ClassSessionCreate(BaseModel):
    course_id: int
    title: str | None = None


class ClassSessionResponse(BaseModel):
    id: int
    course_id: int
    title: str | None
    is_active: bool
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceMarkRequest(BaseModel):
    token: str


class AttendanceRecordResponse(BaseModel):
    id: int
    session_id: int
    course_name: str
    student_id: int
    marked_at: datetime | None

    class Config:
        from_attributes = True


class AttendanceRecordDetailResponse(BaseModel):
    id: int
    session_id: int
    student_id: int
    student_name: str
    roll_no: str | None
    marked_at: datetime

    class Config:
        from_attributes = True


class AttendanceHistoryResponse(BaseModel):
    session_id: int
    course_id: int
    course_code: str
    course_name: str
    session_title: str | None
    session_date: datetime | None
    marked_at: datetime | None

    class Config:
        from_attributes = True


class CourseSessionStats(BaseModel):
    id: int
    title: str
    started_at: datetime | None

    total_present: int
    total_students: int
    attendance_percentage: float
