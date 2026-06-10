from pydantic import BaseModel, EmailStr
from enum import Enum


class Role(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Role


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: Role

    class Config:
        from_attributes = True
