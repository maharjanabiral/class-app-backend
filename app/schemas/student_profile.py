from typing import BaseModel, Optional


class ClassroomMini(BaseModel):
    id: int
    name: str


class StudentProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    student_id: Optional[str]
    roll_no: Optional[int]
    phone: Optional[str]
    classroom: Optional[ClassroomMini]
