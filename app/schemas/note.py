from pydantic import BaseModel
from datetime import datetime


class NoteResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    course_id: int
    teacher_id: int
    created_at: datetime

    class Config:
        from_attributes = True
