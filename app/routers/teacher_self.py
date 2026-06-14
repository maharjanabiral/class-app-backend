"""
Teacher self-service endpoints: /teacher/me/...

Mounted under /teacher prefix in main.py, giving:
  GET /teacher/me/classroom       — their classroom info
  GET /teacher/me/courses         — courses they teach
  GET /teacher/me/courses/{id}/sessions — sessions for a specific course
"""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_teacher
from app.models.teacher import Teacher
from app.models.course import Course
from app.models.classroom import Classroom
from app.models.class_session import ClassSession
from app.models.user import User
from app.schemas.course import CourseDetailResponse, TeacherBrief, ClassroomBrief
from app.schemas.classroom import ClassroomResponse, StudentInClassroom
from app.schemas.attendance import ClassSessionResponse
from app.models.student import Student

router = APIRouter(prefix="/me", tags=["Teacher - Self Service"])

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def _get_teacher(current_user: User, db: AsyncSession) -> Teacher:
    result = await db.execute(
        select(Teacher).where(Teacher.user_id == current_user.id)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found for current user",
        )
    return teacher


@router.get(
    "/courses",
    response_model=List[CourseDetailResponse],
    summary="Get all courses taught by the logged-in teacher",
)
async def get_my_courses(
    db: DBSession,
    current_user: User = Depends(get_current_teacher),
):
    teacher = await _get_teacher(current_user, db)

    result = await db.execute(
        select(Course)
        .options(
            joinedload(Course.teacher).joinedload(Teacher.user),
            joinedload(Course.classroom),
        )
        .where(Course.teacher_id == teacher.id)
    )
    courses = result.scalars().unique().all()

    return [
        {
            "id": c.id,
            "course_code": c.course_code,
            "course_name": c.course_name,
            "classroom": ClassroomBrief(
                id=c.classroom.id,
                name=c.classroom.name,
                section=c.classroom.section,
                academic_year=c.classroom.academic_year,
            ) if c.classroom else None,
            "teacher": TeacherBrief(
                id=teacher.id,
                teacher_id=teacher.teacher_id,
                name=current_user.name,
            ),
        }
        for c in courses
    ]


@router.get(
    "/classroom",
    response_model=List[ClassroomResponse],
    summary="Get classrooms where the logged-in teacher teaches",
)
async def get_my_classrooms(
    db: DBSession,
    current_user: User = Depends(get_current_teacher),
):
    teacher = await _get_teacher(current_user, db)

    # Distinct classrooms via courses
    result = await db.execute(
        select(Classroom)
        .join(Course, Course.class_id == Classroom.id)
        .where(Course.teacher_id == teacher.id)
        .distinct()
    )
    classrooms = result.scalars().all()
    return classrooms


@router.get(
    "/classroom/{classroom_id}/students",
    response_model=List[StudentInClassroom],
    summary="List students in one of the teacher's classrooms",
)
async def get_my_classroom_students(
    classroom_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_teacher),
):
    teacher = await _get_teacher(current_user, db)

    # Ensure teacher has a course in this classroom
    course_check = await db.execute(
        select(Course).where(
            Course.class_id == classroom_id,
            Course.teacher_id == teacher.id,
        )
    )
    if not course_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not teach any course in this classroom",
        )

    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))
        .where(Student.class_id == classroom_id)
    )
    students = result.scalars().all()
    return [
        StudentInClassroom(
            id=s.id,
            student_id=s.student_id,
            roll_no=s.roll_no,
            name=s.user.name,
            email=s.user.email,
            is_active=s.user.is_active,
        )
        for s in students
    ]


@router.get(
    "/courses/{course_id}/sessions",
    response_model=List[ClassSessionResponse],
    summary="List all sessions for one of the teacher's courses",
)
async def get_my_course_sessions(
    course_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_teacher),
):
    teacher = await _get_teacher(current_user, db)

    # Verify teacher owns this course
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if course.teacher_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")

    result = await db.execute(
        select(ClassSession).where(ClassSession.course_id == course_id)
    )
    return result.scalars().all()
