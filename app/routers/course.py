from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin, get_current_staff
from app.models.course import Course
from app.models.classroom import Classroom
from app.models.teacher import Teacher
from app.models.user import User, Role
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseDetailResponse,
    TeacherBrief,
    ClassroomBrief,
)

router = APIRouter()

DBSession = Annotated[AsyncSession, Depends(get_db)]


def _build_detail(course: Course) -> dict:
    """Build CourseDetailResponse dict from an eagerly loaded course."""
    teacher_data = None
    if course.teacher:
        teacher_data = TeacherBrief(
            id=course.teacher.id,
            teacher_id=course.teacher.teacher_id,
            name=course.teacher.user.name,
        )
    classroom_data = None
    if course.classroom:
        classroom_data = ClassroomBrief(
            id=course.classroom.id,
            name=course.classroom.name,
            section=course.classroom.section,
            academic_year=course.classroom.academic_year,
        )
    return {
        "id": course.id,
        "course_code": course.course_code,
        "course_name": course.course_name,
        "classroom": classroom_data,
        "teacher": teacher_data,
    }


@router.post(
    "/",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course (Admin only)",
)
async def create_course(
    data: CourseCreate,
    db: DBSession,
    _=Depends(get_current_admin),
):
    # Verify classroom exists
    # classroom = await db.get(Classroom, data.class_id)
    # if not classroom:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
    #
    # # Verify teacher exists if provided
    # if data.teacher_id is not None:
    #     teacher = await db.get(Teacher, data.teacher_id)
    #     if not teacher:
    #         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    #
    # Ensure course_code is unique
    existing = await db.execute(select(Course).where(Course.course_code == data.course_code))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course with code '{data.course_code}' already exists",
        )

    course = Course(
        course_code=data.course_code,
        course_name=data.course_name,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get(
    "/",
    response_model=List[CourseDetailResponse],
    summary="List all courses (Admin only)",
)
async def list_courses(
    db: DBSession,
    _=Depends(get_current_admin),
):
    result = await db.execute(
        select(Course)
        .options(
            joinedload(Course.teacher).joinedload(Teacher.user),
            joinedload(Course.classroom),
        )
    )
    courses = result.scalars().unique().all()
    return [_build_detail(c) for c in courses]


@router.get(
    "/{course_id}",
    response_model=CourseDetailResponse,
    summary="Get course detail (Admin or assigned Teacher)",
)
async def get_course(
    course_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff),
):
    result = await db.execute(
        select(Course)
        .options(
            joinedload(Course.teacher).joinedload(Teacher.user),
            joinedload(Course.classroom),
        )
        .where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Teachers can only view their own courses
    if current_user.role == Role.teacher:
        teacher_result = await db.execute(
            select(Teacher).where(Teacher.user_id == current_user.id)
        )
        teacher = teacher_result.scalar_one_or_none()
        if not teacher or course.teacher_id != teacher.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    return _build_detail(course)


@router.patch(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Update a course (Admin only)",
)
async def update_course(
    course_id: int,
    data: CourseUpdate,
    db: DBSession,
    _=Depends(get_current_admin),
):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if data.course_name is not None:
        course.course_name = data.course_name

    # if data.class_id is not None:
    #     classroom = await db.get(Classroom, data.class_id)
    #     if not classroom:
    #         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
    #     course.classroom_id = data.class_id
    #
    # if data.teacher_id is not None:
    #     teacher = await db.get(Teacher, data.teacher_id)
    #     if not teacher:
    #         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    #     course.teacher_id = data.teacher_id
    #
    if data.course_code is not None:
        course.course_code = data.course_code
    await db.commit()
    await db.refresh(course)
    return course


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a course (Admin only)",
)
async def delete_course(
    course_id: int,
    db: DBSession,
    _=Depends(get_current_admin),
):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    await db.delete(course)
    await db.commit()
