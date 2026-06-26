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
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CourseOut(BaseModel):
    id: int
    course_name: str
    course_code: str | None = None

    class Config:
        from_attributes = True


class ClassroomOut(BaseModel):
    id: int
    name: str
    section: str | None = None

    courses: list[CourseOut] = []

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: Role

    class Config:
        from_attributes = True


class UserProfileOut(BaseModel):
    id: int
    name: str
    email: str
    role: Role

    classrooms: list[ClassroomOut] = []
    courses: list[CourseOut] = []

    class Config:
        from_attributes = True
