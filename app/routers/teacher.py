from typing import Annotated, List

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.teacher import Teacher
from app.schemas.teacher import (
    TeacherCreate,
    TeacherResponse
)
from app.dependencies import (
    get_current_admin
)


router = APIRouter(
    prefix="/teacher",
    tags=["Teachers"]
)

DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/", response_model=TeacherResponse)
async def create_teacher(data: TeacherCreate, db: DBSession, current_user=Depends(get_current_admin)): 
    teacher = Teacher(**data.model_dump())

    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)

    return teacher


@router.get("/", response_model=List[TeacherResponse])
async def get_teacher(db: DBSession):
    result = await db.execute(select(Teacher))
    return result.scalars().all()
