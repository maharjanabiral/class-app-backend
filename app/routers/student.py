from typing import Annotated, List

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.student import Student
from app.schemas.student import (
    StudentCreate,
    StudentResponse
)
from app.dependencies import (
    get_current_admin
)


router = APIRouter(
    prefix="/students",
    tags=["Students"]
)

DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/", response_model=StudentResponse)
async def create_student(data: StudentCreate, db: DBSession, current_user=Depends(get_current_admin)): 
    student = Student(**data.model_dump())

    db.add(student)
    await db.commit()
    await db.refresh(student)

    return student


@router.get("/", response_model=List[StudentResponse])
async def get_student(db: DBSession):
    result = await db.execute(select(Student))
    return result.scalars().all()
