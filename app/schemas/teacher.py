from pydantic import BaseModel


class TeacherCreate(BaseModel):
    user_id: int
    department: str
    phone: str | None = None


class TeacherResponse(BaseModel):
    id: int
    user_id: int
    department: str
    phone: str | None

    class Config:
        from_attributes = True
