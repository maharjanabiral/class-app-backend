from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class StudentCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    roll_no: str
    phone: str | None = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class UserInfo(BaseModel):
    id: int
    name: str
    email: Optional[str]
    is_active: bool
    login_id: Optional[str]

    class Config:
        from_attributes = True


class StudentCreateResponse(BaseModel):
    student_id: str
    default_password: str
    user: UserInfo

    class Config:
        from_attributes = True


class StudentResponse(BaseModel):
    id: int
    student_id: str
    user_id: int
    roll_no: Optional[str] = None
    phone: Optional[str] = None
    user: UserInfo
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
