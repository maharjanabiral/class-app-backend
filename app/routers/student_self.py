"""
Student self-service endpoints: /student/me/...

Mounted under /student prefix in main.py, giving:
  GET /student/me/classroom      — the student's classroom info
  GET /student/me/courses        — courses in their classroom
  GET /student/me/attendance     — own attendance records per course/session
"""
from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_student
from app.models.student import Student
from app.models.classroom import Classroom
from app.models.course import Course
from app.models.class_session import ClassSession
from app.models.attendance_record import AttendanceRecord
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.classroom import ClassroomResponse, CourseInClassroom

router = APIRouter(prefix="/me", tags=["Student - Self Service"])

DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Response schema (local to this module) ────────────────────────────────────

class MyAttendanceRecord(BaseModel):
    session_id: int
    session_title: Optional[str] = None
    course_code: str
    course_name: str
    marked_at: datetime

    class Config:
        from_attributes = True


class AttendanceSummaryResponse(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    total_sessions: int
    attended: int
    attendance_percentage: float
    records: List[MyAttendanceRecord]


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_student(current_user: User, db: AsyncSession) -> Student:
    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))
        .where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for current user",
        )
    return student


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/classroom",
    response_model=ClassroomResponse,
    summary="Get the classroom the logged-in student belongs to",
)
async def get_my_classroom(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    student = await _get_student(current_user, db)

    if not student.class_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not been assigned to a classroom yet",
        )

    classroom = await db.get(Classroom, student.class_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    return classroom


@router.get(
    "/courses",
    response_model=List[CourseInClassroom],
    summary="Get all courses in the student's classroom",
)
async def get_my_courses(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    student = await _get_student(current_user, db)

    if not student.class_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not been assigned to a classroom yet",
        )

    result = await db.execute(
        select(Course)
        .options(joinedload(Course.teacher).joinedload(Teacher.user))
        .where(Course.class_id == student.class_id)
    )
    courses = result.scalars().all()
    return [
        CourseInClassroom(
            id=c.id,
            course_code=c.course_code,
            course_name=c.course_name,
            teacher_name=c.teacher.user.name if c.teacher else None,
        )
        for c in courses
    ]


@router.get(
    "/attendance",
    response_model=List[AttendanceSummaryResponse],
    summary="Get own attendance summary grouped by course",
)
async def get_my_attendance(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    student = await _get_student(current_user, db)

    if not student.class_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not been assigned to a classroom yet",
        )

    # Get all courses in student's classroom
    courses_result = await db.execute(
        select(Course)
        .options(joinedload(Course.teacher).joinedload(Teacher.user))
        .where(Course.class_id == student.class_id)
    )
    courses = courses_result.scalars().all()

    summary = []
    for course in courses:
        # Total sessions for this course
        sessions_result = await db.execute(
            select(ClassSession).where(ClassSession.course_id == course.id)
        )
        sessions = sessions_result.scalars().all()
        total_sessions = len(sessions)
        session_map = {s.id: s for s in sessions}

        # Student's attendance records for sessions of this course
        if not session_map:
            summary.append(
                AttendanceSummaryResponse(
                    course_id=course.id,
                    course_code=course.course_code,
                    course_name=course.course_name,
                    total_sessions=0,
                    attended=0,
                    attendance_percentage=0.0,
                    records=[],
                )
            )
            continue

        records_result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(list(session_map.keys())),
            )
        )
        records = records_result.scalars().all()
        attended = len(records)

        percentage = round((attended / total_sessions) * 100, 2) if total_sessions > 0 else 0.0

        record_details = [
            MyAttendanceRecord(
                session_id=r.session_id,
                session_title=session_map[r.session_id].title,
                course_code=course.course_code,
                course_name=course.course_name,
                marked_at=r.marked_at,
            )
            for r in records
        ]

        summary.append(
            AttendanceSummaryResponse(
                course_id=course.id,
                course_code=course.course_code,
                course_name=course.course_name,
                total_sessions=total_sessions,
                attended=attended,
                attendance_percentage=percentage,
                records=record_details,
            )
        )

    return summary
