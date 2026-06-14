import io
import csv
# pyrefly: ignore [untyped-import]
import qrcode
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.dependencies import get_current_student, get_current_staff, get_current_user
from app.models.user import User, Role
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.course import Course
from app.models.class_session import ClassSession
from app.models.attendance_record import AttendanceRecord
from app.core.security import create_qr_token, decode_qr_token
from app.schemas.attendance import (
    ClassSessionCreate,
    ClassSessionResponse,
    AttendanceMarkRequest,
    AttendanceRecordResponse,
    AttendanceRecordDetailResponse,
)

router = APIRouter(
    prefix="/attendance",
    tags=["Attendance"]
)

DBSession = Annotated[AsyncSession, Depends(get_db)]

# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_teacher(user_id: int, db: AsyncSession) -> Teacher:
    result = await db.execute(select(Teacher).where(Teacher.user_id == user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=403, detail="Current user is not registered as a teacher")
    return teacher

async def _get_student(user_id: int, db: AsyncSession) -> Student:
    result = await db.execute(select(Student).where(Student.user_id == user_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=400, detail="Current user does not have a student profile")
    return student

async def _verify_teacher_course_access(teacher_id: int, course_id: int, db: AsyncSession):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Not authorized for this course")
    return course

async def _verify_teacher_session_access(teacher_id: int, session: ClassSession, db: AsyncSession):
    result = await db.execute(select(Course).where(Course.id == session.course_id))
    course = result.scalar_one_or_none()
    if not course or course.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Not authorized for this session")
    return course

# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/export")
async def export_session_attendance(
    session_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff)
):
    """Export attendance for a specific session to CSV."""
    result = await db.execute(
        select(ClassSession)
        .options(joinedload(ClassSession.course))
        .where(ClassSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Basic Teacher Check
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_session_access(teacher.id, session, db)

    # Fetch records
    records_result = await db.execute(
        select(AttendanceRecord)
        .options(joinedload(AttendanceRecord.student).joinedload(Student.user))
        .where(AttendanceRecord.session_id == session_id)
    )
    records = records_result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student ID", "Roll No", "Name", "Email", "Marked At"])

    for r in records:
        writer.writerow([
            r.student.student_id,
            r.student.roll_no or "N/A",
            r.student.user.name,
            r.student.user.email,
            r.marked_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    output.seek(0)
    filename = f"attendance_{session.course.course_code}_{session_id}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ─── NEW: Teacher — list their own sessions ───────────────────────────────────

@router.get(
    "/sessions",
    response_model=List[ClassSessionResponse],
    summary="List sessions (Teacher: their own courses; Admin: optionally filter by course_id)",
)
async def list_sessions(
    db: DBSession,
    course_id: Optional[int] = Query(default=None, description="Filter by course ID"),
    current_user: User = Depends(get_current_staff),
):
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        # Get course IDs for this teacher
        courses_q = select(Course.id).where(Course.teacher_id == teacher.id)
        if course_id is not None:
            courses_q = courses_q.where(Course.id == course_id)

        course_ids_result = await db.execute(courses_q)
        course_ids = [row[0] for row in course_ids_result.all()]

        if not course_ids:
            return []

        query = select(ClassSession).where(ClassSession.course_id.in_(course_ids))
    else:
        # Admin
        query = select(ClassSession)
        if course_id is not None:
            query = query.where(ClassSession.course_id == course_id)

    result = await db.execute(query)
    return result.scalars().all()


# ─── NEW: Student — view their own attendance records ────────────────────────

@router.get(
    "/my-records",
    response_model=List[AttendanceRecordResponse],
    summary="Get the logged-in student's own attendance records",
)
async def get_my_attendance_records(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    student = await _get_student(current_user.id, db)
    records_result = await db.execute(
        select(AttendanceRecord).where(AttendanceRecord.student_id == student.id)
    )
    return records_result.scalars().all()

@router.post("/sessions", response_model=ClassSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: ClassSessionCreate,
    db: DBSession,
    current_user: User = Depends(get_current_staff)
):
    # If the user is a teacher, verify they are assigned to this course
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_course_access(teacher.id, data.course_id, db)
    else:
        course_result = await db.execute(select(Course).where(Course.id == data.course_id))
        course = course_result.scalar_one_or_none()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )

    session = ClassSession(
        course_id=data.course_id,
        title=data.title
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}/qr")
async def generate_session_qr(
    session_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff)
):
    # Fetch session
    result = await db.execute(select(ClassSession).where(ClassSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class session not found"
        )

    # Verify authorization
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_session_access(teacher.id, session, db)

    # Generate QR token (expires in 2 minutes / 120 seconds)
    # pyrefly: ignore [bad-argument-type]
    token = create_qr_token(session.id, expires_delta_seconds=120)

    # Generate QR Code Image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    # pyrefly: ignore [unexpected-keyword]
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.post("/mark", response_model=AttendanceRecordResponse, status_code=status.HTTP_200_OK)
async def mark_attendance(
    payload: AttendanceMarkRequest,
    db: DBSession,
    current_user: User = Depends(get_current_student)
):
    # Validate Student profile
    student = await _get_student(current_user.id, db)
    # Validate QR Token
    qr_payload = decode_qr_token(payload.token)
    if not qr_payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired attendance token"
        )

    session_id = int(qr_payload["sub"])

    # Fetch Session and Course
    session_result = await db.execute(select(ClassSession).where(ClassSession.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class session not found"
        )

    course_result = await db.execute(select(Course).where(Course.id == session.course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course associated with class session not found"
        )

    # Verify student belongs to the classroom/course
    if student.class_id != course.class_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student does not belong to the class assigned to this course"
        )

    # Check if student is already marked present
    record_result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.student_id == student.id
        )
    )
    existing_record = record_result.scalar_one_or_none()
    if existing_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance has already been marked for this session"
        )

    # Record attendance
    record = AttendanceRecord(
        session_id=session.id,
        student_id=student.id
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return record


@router.get("/sessions/{session_id}/records", response_model=List[AttendanceRecordDetailResponse])
async def get_session_attendance_records(
    session_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff)
):
    # Fetch session
    result = await db.execute(select(ClassSession).where(ClassSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class session not found"
        )

    # Verify authorization
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_session_access(teacher.id, session, db)

    # Fetch marked records with student & user details loaded
    records_result = await db.execute(
        select(AttendanceRecord)
        .options(joinedload(AttendanceRecord.student).joinedload(Student.user))
        .where(AttendanceRecord.session_id == session_id)
    )
    records = records_result.scalars().all()

    response_data = []
    for r in records:
        response_data.append({
            "id": r.id,
            "session_id": r.session_id,
            "student_id": r.student_id,
            "student_name": r.student.user.name,
            "roll_no": r.student.roll_no,
            "marked_at": r.marked_at
        })

    return response_data
