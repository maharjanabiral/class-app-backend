# app/schemas/teacher.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# --- used by admin when creating a teacher ---
class TeacherCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    phone: Optional[str] = None


# --- used by admin when updating a teacher ---
class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


# --- nested user info inside teacher response ---
class UserInfo(BaseModel):
    id: int
    name: str
    email: Optional[str]
    is_active: bool
    login_id: Optional[str]

    class Config:
        from_attributes = True


# --- returned to admin after creation (includes default password) ---
class TeacherCreateResponse(BaseModel):
    teacher_id: str
    default_password: str       # shown once to admin
    user: UserInfo

    class Config:
        from_attributes = True


# --- general teacher profile response ---
class TeacherResponse(BaseModel):
    id: int
    teacher_id: str
    department: Optional[str]
    phone: Optional[str]
    user: UserInfo
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
