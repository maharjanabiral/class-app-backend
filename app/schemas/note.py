from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NoteCreate(BaseModel):
    title: str
    description: Optional[str] = None
    class_course_id: int


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class CLassCourseInfo(BaseModel):
    id: int
    class_id: int
    course_id: int
    teacher_id: int

    class Config:
        from_attributes = True


class NoteResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None

    file_name: str
    file_path: str

    class_course_id: int

    created_at: datetime

    # Optional nested object (recommended for frontend)
    class_course: Optional[CLassCourseInfo] = None

    class Config:
        from_attributes = True
