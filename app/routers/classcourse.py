from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.classcourse import ClassCourse
from app.schemas.classcourse import ClassCourseCreate
from app.dependencies import get_current_admin

router = APIRouter(
)


# -------------------------
# CREATE CLASSCOURSE
# -------------------------
@router.post("/")
async def create_class_course(
    data: ClassCourseCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):

    class_course = ClassCourse(
        class_id=1,
        course_id=1,
        teacher_id=1
    )

    db.add(class_course)
    await db.commit()
    await db.refresh(class_course)

    return class_course


# -------------------------
# GET ALL CLASSCOURSES
# -------------------------
@router.get("/")
async def get_all_class_courses(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    result = await db.execute(select(ClassCourse))
    return result.scalars().all()


# -------------------------
# GET SINGLE CLASSCOURSE
# -------------------------
@router.get("/{class_course_id}")
async def get_class_course(
    class_course_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    result = await db.execute(
        select(ClassCourse).where(ClassCourse.id == class_course_id)
    )

    class_course = result.scalar_one_or_none()

    if not class_course:
        raise HTTPException(
            status_code=404,
            detail="ClassCourse not found"
        )

    return class_course


# -------------------------
# UPDATE CLASSCOURSE (optional but useful)
# -------------------------
@router.put("/{class_course_id}")
async def update_class_course(
    class_course_id: int,
    data: ClassCourseCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    result = await db.execute(
        select(ClassCourse).where(ClassCourse.id == class_course_id)
    )

    class_course = result.scalar_one_or_none()

    if not class_course:
        raise HTTPException(
            status_code=404,
            detail="ClassCourse not found"
        )

    # update values
    class_course.class_id = data.class_id
    class_course.course_id = data.course_id
    class_course.teacher_id = data.teacher_id

    await db.commit()
    await db.refresh(class_course)

    return class_course


# -------------------------
# DELETE CLASSCOURSE
# -------------------------
@router.delete("/{class_course_id}")
async def delete_class_course(
    class_course_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    result = await db.execute(
        select(ClassCourse).where(ClassCourse.id == class_course_id)
    )

    class_course = result.scalar_one_or_none()

    if not class_course:
        raise HTTPException(
            status_code=404,
            detail="ClassCourse not found"
        )

    await db.delete(class_course)
    await db.commit()

    return {
        "message": "ClassCourse deleted successfully"
    }
