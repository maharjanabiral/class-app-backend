from pydantic import BaseModel


class StudentCreate(BaseModel):
    user_id: int
    class_id: int
    roll_no: str
    phone: str | None = None


class StudentResponse(BaseModel):
    id: int
    user_id: int
    class_id: int
    roll_no: str
    phone: str | None

    class Config:
        from_attributes = True
