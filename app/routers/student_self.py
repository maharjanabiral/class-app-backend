from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user, get_current_student
from app.models.student import Student
from app.models.classroom import Classroom
from app.models.course import Course
from app.models.class_session import ClassSession
from app.models.attendance_record import AttendanceRecord
from app.models.teacher import Teacher
from app.models.user import User
from app.schemas.classroom import ClassroomResponse, CourseInClassroom
from app.schemas.attendance import AttendanceHistoryResponse

router = APIRouter(prefix="/me", tags=["Student - Self Service"])

DBSession = Annotated[AsyncSession, Depends(get_db)]


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

class CourseSessionResponse(BaseModel):
    session_id: int
    title: str | None
    started_at: datetime | None
    attended: bool


class CourseDetailResponse(BaseModel):
    id: int
    course_code: str
    course_name: str
    teacher_name: str | None

    total_sessions: int
    attended_sessions: int
    attendance_percentage: float

    sessions: list[CourseSessionResponse]


async def _get_student(current_user: User, db: AsyncSession) -> Student:
    try:
        result = await db.execute(
            select(Student).where(Student.user_id == current_user.id)
        )

        student = result.scalar_one_or_none()
        print(f"----------------student: {student}")

        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student profile not found",
            )

        return student

    except HTTPException:
        raise
    except Exception as e:
        print("Error loading student:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load student profile",
        )

@router.get(
    "/classroom",
    response_model=Optional[ClassroomResponse],
)
async def get_my_classroom(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    try:
        student = await _get_student(current_user, db)

        if not student.classroom_id:
            return None

        classroom = await db.get(Classroom, student.classroom_id)

        if not classroom:
            return None

        return classroom

    except HTTPException:
        raise
    except Exception as e:
        print("Classroom error:", str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch classroom",
        )



@router.get(
    "/courses",
    response_model=List[CourseInClassroom],
)
async def get_my_courses(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    try:
        student = await _get_student(current_user, db)

        if not student.classroom_id:
            return []

        result = await db.execute(
            select(Course)
            .options(
                joinedload(Course.teacher)
                .joinedload(Teacher.user)
            )
            .where(Course.classroom_id == student.classroom_id)
        )

        courses = result.scalars().all()

        return [
            CourseInClassroom(
                id=c.id,
                course_code=c.course_code,
                course_name=c.course_name,
                teacher_name=c.teacher.user.name
                if c.teacher and c.teacher.user
                else None,
            )
            for c in courses
        ]

    except HTTPException:
        raise
    except Exception as e:
        print("Courses error:", str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch courses",
        )

@router.get(
    "/attendance",
    response_model=List[AttendanceSummaryResponse],
)
async def get_my_attendance(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    try:
        student = await _get_student(current_user, db)

        if not student.classroom_id:
            return []

        courses_result = await db.execute(
            select(Course)
            .options(
                joinedload(Course.teacher)
                .joinedload(Teacher.user)
            )
            .where(Course.classroom_id == student.classroom_id)
        )

        courses = courses_result.scalars().all()

        summary = []

        for course in courses:
            sessions_result = await db.execute(
                select(ClassSession).where(
                    ClassSession.course_id == course.id
                )
            )

            sessions = sessions_result.scalars().all()

            total_sessions = len(sessions)
            session_map = {s.id: s for s in sessions}

            if not session_map:
                summary.append(
                    AttendanceSummaryResponse(
                        course_id=course.id,
                        course_code=course.course_code,
                        course_name=course.course_name,
                        total_sessions=0,
                        attended=0,
                        attendance_percentage=0,
                        records=[],
                    )
                )
                continue

            records_result = await db.execute(
                select(AttendanceRecord).where(
                    AttendanceRecord.student_id == student.id,
                    AttendanceRecord.session_id.in_(
                        list(session_map.keys())
                    ),
                )
            )

            records = records_result.scalars().all()
            attended = len(records)

            percentage = (
                round((attended / total_sessions) * 100, 2)
                if total_sessions > 0
                else 0
            )

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

    except HTTPException:
        raise
    except Exception as e:
        print("Attendance error:", str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch attendance",
        )


# @router.get(
#     "/my-records",
#     response_model=List[AttendanceRecordResponse],
#     summary="Get the logged-in student's own attendance records",
# )
# async def get_my_attendance_records(
#     db: DBSession,
#     current_user: User = Depends(get_current_student),
# ):
#     student = await _get_student(current_user, db)
#     records_result = await db.execute(
#         select(AttendanceRecord).where(AttendanceRecord.student_id == student.id)
#     )
#     print(records_result)
#     # return records_result.scalars().all()

@router.get(
    "/my-records",
    response_model=list[AttendanceHistoryResponse],
)
async def get_my_attendance_history(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    student = await _get_student(current_user, db)

    if not student.classroom_id:
        return []

    sessions_result = await db.execute(
        select(ClassSession)
        .options(
            joinedload(ClassSession.course)
        )
        .join(Course)
        .where(
            Course.classroom_id == student.classroom_id
        )
        .order_by(ClassSession.created_at.desc())
    )

    sessions = sessions_result.scalars().all()

    if not sessions:
        return []

    session_ids = [s.id for s in sessions]

    records_result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.session_id.in_(session_ids),
        )
    )

    records = records_result.scalars().all()

    record_map = {
        record.session_id: record
        for record in records
    }

    return [
        AttendanceHistoryResponse(
            session_id=session.id,
            course_id=session.course.id,
            course_code=session.course.course_code,
            course_name=session.course.course_name,
            session_title=session.title,
            session_date=session.started_at,
            marked_at=record_map.get(session.id).marked_at
            if session.id in record_map
            else None,
        )
        for session in sessions
    ]


@router.get(
    "/courses/{course_id}",
    response_model=CourseDetailResponse,
)
async def get_course_detail(
    course_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    student = await _get_student(current_user, db)

    course_result = await db.execute(
        select(Course)
        .options(
            joinedload(Course.teacher)
            .joinedload(Teacher.user)
        )
        .where(
            Course.id == course_id,
            Course.classroom_id == student.classroom_id,
        )
    )

    course = course_result.scalar_one_or_none()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found",
        )

    sessions_result = await db.execute(
        select(ClassSession)
        .where(ClassSession.course_id == course.id)
        .order_by(ClassSession.started_at.desc())
    )

    sessions = sessions_result.scalars().all()

    session_ids = [s.id for s in sessions]

    records_result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.session_id.in_(session_ids),
        )
    )

    records = records_result.scalars().all()

    attended_session_ids = {
        record.session_id
        for record in records
    }

    total_sessions = len(sessions)
    attended_sessions = len(attended_session_ids)

    attendance_percentage = (
        round((attended_sessions / total_sessions) * 100, 2)
        if total_sessions > 0
        else 0
    )

    return CourseDetailResponse(
        id=course.id,
        course_code=course.course_code,
        course_name=course.course_name,
        teacher_name=(
            course.teacher.user.name
            if course.teacher and course.teacher.user
            else None
        ),
        total_sessions=total_sessions,
        attended_sessions=attended_sessions,
        attendance_percentage=attendance_percentage,
        sessions=[
            CourseSessionResponse(
                session_id=session.id,
                title=session.title,
                started_at=session.started_at,
                attended=session.id in attended_session_ids,
            )
            for session in sessions
        ],
    )
