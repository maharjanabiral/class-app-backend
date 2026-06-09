from typing import Annotated, List

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.classroom import Classroom
from app.schemas.classroom import (
    ClassroomCreate,
    ClassroomResponse
)
from app.dependencies import (
    get_current_admin
)


router = APIRouter(
    prefix="/classroom",
    tags=["Classrooms"]
)

DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/", response_model=ClassroomResponse)
async def create_classroom(data: ClassroomCreate, db: DBSession, current_user=Depends(get_current_admin)): 
    classroom = Classroom(**data.model_dump())

    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)

    return classroom


@router.get("/", response_model=List[ClassroomResponse])
async def get_classroom(db: DBSession):
    result = await db.execute(select(Classroom))
    return result.scalars().all()
