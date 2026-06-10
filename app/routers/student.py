# app/routers/student.py
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_admin
from app.services.admin_service import create_student
from app.models.student import Student
from app.schemas.student import (
    StudentCreate,
    StudentCreateResponse,
    StudentResponse,
    StudentUpdate,
)

router = APIRouter()  # no prefix here — admin.py will mount it with a prefix

DBSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[None, Depends(get_current_admin)]


@router.post(
    "/",
    response_model=StudentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a student account"
)
async def create_student_account(data: StudentCreate, db: DBSession, _: AdminUser):
    return await create_student(db, data)


@router.get("/", response_model=List[StudentResponse])
async def get_all_students(db: DBSession, _: AdminUser):
    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))  # ← eagerly load user
    )
    return result.scalars().all()


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get a student by student_id"
)
async def get_student(student_id: str, db: DBSession, _: AdminUser):
    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))  # ← eagerly load user
        .filter(Student.student_id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    data: StudentUpdate,
    db: DBSession,
    _: AdminUser
):
    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))  # ← add this
        .filter(Student.student_id == student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    for field in ("phone", "roll_no"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(student, field, value)

    for field in ("name", "email", "is_active"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(student.user, field, value)

    await db.commit()
    await db.refresh(student)
    return student


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a student account"
)
async def delete_student(student_id: str, db: DBSession, _: AdminUser):
    result = await db.execute(select(Student).options(joinedload(Student.user)).filter(Student.student_id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    await db.delete(student.user)
    await db.commit()
