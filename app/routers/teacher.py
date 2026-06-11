from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_admin
from app.services.admin_service import create_teacher
from app.models.teacher import Teacher
from app.schemas.teacher import (
    TeacherCreate,
    TeacherCreateResponse,
    TeacherResponse,
    TeacherUpdate,
)

router = APIRouter()

DBSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[None, Depends(get_current_admin)]


@router.post(
    "/",
    response_model=TeacherCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a teacher account"
)
async def create_teacher_account(data: TeacherCreate, db: DBSession, _: AdminUser):
    return await create_teacher(db, data)


@router.get(
    "/",
    response_model=List[TeacherResponse],
    summary="Get all teachers"
)
async def get_all_teachers(db: DBSession, _: AdminUser):
    result = await db.execute(
        select(Teacher).options(joinedload(Teacher.user))
    )
    return result.scalars().all()


@router.get(
    "/{teacher_id}",
    response_model=TeacherResponse,
    summary="Get a teacher by teacher_id"
)
async def get_teacher(teacher_id: str, db: DBSession, _: AdminUser):
    result = await db.execute(
        select(Teacher)
        .options(joinedload(Teacher.user))
        .filter(Teacher.teacher_id == teacher_id)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    return teacher


@router.patch(
    "/{teacher_id}",
    response_model=TeacherResponse,
    summary="Update a teacher"
)
async def update_teacher(teacher_id: str, data: TeacherUpdate, db: DBSession, _: AdminUser):
    result = await db.execute(
        select(Teacher)
        .options(joinedload(Teacher.user))
        .filter(Teacher.teacher_id == teacher_id)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    for field in ("department", "phone"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(teacher, field, value)

    for field in ("name", "email", "is_active"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(teacher.user, field, value)

    await db.commit()
    await db.refresh(teacher)
    return teacher


@router.delete(
    "/{teacher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a teacher account"
)
async def delete_teacher(teacher_id: str, db: DBSession, _: AdminUser):
    result = await db.execute(
        select(Teacher)
        .options(joinedload(Teacher.user))
        .filter(Teacher.teacher_id == teacher_id)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    await db.delete(teacher.user)
    await db.commit()
