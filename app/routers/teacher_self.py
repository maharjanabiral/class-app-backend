"""
Teacher self-service endpoints: /teacher/me/...

Mounted under /teacher prefix in main.py, giving:
  GET /teacher/me/classroom       — their classroom info
  GET /teacher/me/courses         — courses they teach
  GET /teacher/me/courses/{id}/sessions — sessions for a specific course
"""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, exists
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_teacher
from app.models.teacher import Teacher
from app.models.course import Course
from app.models.classroom import Classroom
from app.models.class_session import ClassSession
from app.models.attendance_record import AttendanceRecord
from app.models.user import User
from app.schemas.course import CourseDetailResponse, TeacherBrief, ClassroomBrief, TeacherCourseDetailResponse
from app.schemas.classroom import ClassroomResponse, StudentInClassroom, ClassroomDetail, CourseInClassroom
from app.schemas.attendance import CourseSessionStats
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
        .join(Course, Course.classroom_id == Classroom.id)
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

    # Verify teacher teaches at least one course in this classroom
    course_check = await db.execute(
        select(Course).where(
            Course.classroom_id == classroom_id,
            Course.teacher_id == teacher.id,
        )
    )

    if course_check.first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not teach any course in this classroom",
        )

    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))
        .where(Student.classroom_id == classroom_id)
    )

    students = result.scalars().all()

    return [
        StudentInClassroom(
            id=student.id,
            student_id=student.student_id,
            roll_no=student.roll_no,
            name=student.user.name,
            email=student.user.email,
            is_active=student.user.is_active,
        )
        for student in students
    ]#

@router.get(
    "/classroom/{classroom_id}",
    response_model=ClassroomDetail,
    summary="Get full detail for one of the teacher's classrooms, including its courses and students",
)
async def get_my_classroom_detail(
    classroom_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_teacher),
):
    teacher = await _get_teacher(current_user, db)

    # Verify teacher teaches at least one course in this classroom
    course_check = await db.execute(
        select(Course).where(
            Course.classroom_id == classroom_id,
            Course.teacher_id == teacher.id,
        )
    )
    if course_check.first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not teach any course in this classroom",
        )

    classroom = await db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    # All courses in this classroom (not just this teacher's — students may want the full picture,
    # but here we're on the teacher's own view so showing all courses run in this classroom is fine)
    courses_result = await db.execute(
        select(Course)
        .options(joinedload(Course.teacher).joinedload(Teacher.user))
        .where(Course.classroom_id == classroom_id)
    )
    courses = courses_result.scalars().unique().all()

    students_result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))
        .where(Student.classroom_id == classroom_id)
    )
    students = students_result.scalars().all()

    return ClassroomDetail(
        id=classroom.id,
        name=classroom.name,
        section=classroom.section,
        academic_year=classroom.academic_year,
        students=[
            StudentInClassroom(
                id=s.id,
                student_id=s.student_id,
                roll_no=s.roll_no,
                name=s.user.name,
                email=s.user.email,
                is_active=s.user.is_active,
            )
            for s in students
        ],
        courses=[
            CourseInClassroom(
                id=c.id,
                course_code=c.course_code,
                course_name=c.course_name,
                teacher_name=c.teacher.user.name if c.teacher else None,
            )
            for c in courses
        ],
    )



# @router.get(
#     "/courses/{course_id}/sessions",
#     response_model=List[ClassSessionResponse],
#     summary="List all sessions for one of the teacher's courses",
# )
# async def get_my_course_sessions(
#     course_id: int,
#     db: DBSession,
#     current_user: User = Depends(get_current_teacher),
# ):
#     teacher = await _get_teacher(current_user, db)
#
#     # Verify teacher owns this course
#     course = await db.get(Course, course_id)
#     if not course:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
#     if course.teacher_id != teacher.id:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")
#
#     result = await db.execute(
#         select(ClassSession).where(ClassSession.course_id == course_id)
#     )
#     return result.scalars().all()


@router.get(
    "/courses/{course_id}",
    response_model=TeacherCourseDetailResponse,
)
async def get_course_detail(
    course_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_teacher),
):
    teacher = await _get_teacher(current_user, db)

    course_result = await db.execute(
        select(Course)
        .options(joinedload(Course.classroom))
        .where(
            Course.id == course_id,
            Course.teacher_id == teacher.id,
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
        .where(ClassSession.course_id == course_id)
        .order_by(ClassSession.started_at.desc())
    )

    sessions = sessions_result.scalars().all()

    total_sessions = len(sessions)

    active_session = next(
        (session for session in sessions if session.is_active),
        None,
    )

    total_students_result = await db.execute(
        select(func.count(Student.id))
        .where(Student.classroom_id == course.classroom_id)
    )

    total_students = total_students_result.scalar() or 0
    session_ids = [session.id for session in sessions]

    attendance_map = {}

    if session_ids:
        attendance_result = await db.execute(
            select(
                AttendanceRecord.session_id,
                func.count(AttendanceRecord.id).label("present_count"),
            )
            .where(AttendanceRecord.session_id.in_(session_ids))
            .group_by(AttendanceRecord.session_id)
        )

        attendance_map = {
            session_id: present_count
            for session_id, present_count in attendance_result.all()
        }

    all_sessions = []

    for session in sessions:
        total_present = attendance_map.get(session.id, 0)

        attendance_percentage = (
            round((total_present / total_students) * 100, 2)
            if total_students > 0
            else 0
        )

        all_sessions.append(
            CourseSessionStats(
                id=session.id,
                title=session.title,
                started_at=session.started_at,
                total_present=total_present,
                total_students=total_students,
                attendance_percentage=attendance_percentage,
            )
        )

    active_session_stats = None
    if active_session:
        total_present = attendance_map.get(active_session.id, 0)
        attendance_percentage = (
            round((total_present / total_students) * 100, 2)
            if total_students > 0
            else 0
        )
        active_session_stats = CourseSessionStats(
            id=active_session.id,
            title=active_session.title,
            started_at=active_session.started_at,
            total_present=total_present,
            total_students=total_students,
            attendance_percentage=attendance_percentage,
        )

    return TeacherCourseDetailResponse(
        id=course.id,
        course_code=course.course_code,
        course_name=course.course_name,
        classroom_id=course.classroom.id,
        classroom_name=course.classroom.name,
        total_sessions=total_sessions,
        active_session=active_session_stats,
        all_sessions=all_sessions,
    )
