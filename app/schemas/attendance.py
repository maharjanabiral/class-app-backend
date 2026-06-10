from datetime import datetime
from pydantic import BaseModel


class ClassSessionCreate(BaseModel):
    course_id: int
    title: str | None = None


class ClassSessionResponse(BaseModel):
    id: int
    course_id: int
    title: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceMarkRequest(BaseModel):
    token: str


class AttendanceRecordResponse(BaseModel):
    id: int
    session_id: int
    student_id: int
    marked_at: datetime

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
