from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Student, Teacher, Classroom
from app.schemas.user import UserProfileOut
from app.utils.profile_mapper import build_profile

router = APIRouter(prefix="/user")


@router.get("/profile", response_model=UserProfileOut)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stmt = (
        select(User)
        .options(
            selectinload(User.student)
            .selectinload(Student.classroom)
            .selectinload(Classroom.courses),
            selectinload(User.teacher)
            .selectinload(Teacher.courses),
        )
        .where(User.id == current_user.id)
    )

    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return build_profile(user)
