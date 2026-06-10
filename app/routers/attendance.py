import io
import qrcode
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.dependencies import get_current_student, get_current_staff
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


@router.post("/sessions", response_model=ClassSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: ClassSessionCreate,
    db: DBSession,
    current_user: User = Depends(get_current_staff)
):
    # If the user is a teacher, verify they are assigned to this course
    if current_user.role == Role.teacher:
        result = await db.execute(select(Teacher).where(Teacher.user_id == current_user.id))
        teacher = result.scalar_one_or_none()
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user is not registered as a teacher"
            )

        course_result = await db.execute(select(Course).where(Course.id == data.course_id))
        course = course_result.scalar_one_or_none()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )

        if course.teacher_id != teacher.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to create a session for this course"
            )

    # Verify course exists generally
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
        teacher_result = await db.execute(select(Teacher).where(Teacher.user_id == current_user.id))
        teacher = teacher_result.scalar_one_or_none()
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user is not registered as a teacher"
            )

        course_result = await db.execute(select(Course).where(Course.id == session.course_id))
        course = course_result.scalar_one_or_none()
        if not course or course.teacher_id != teacher.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this session's QR code"
            )

    # Generate QR token (expires in 2 minutes / 120 seconds)
    token = create_qr_token(session.id, expires_delta_seconds=120)

    # Generate QR Code Image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
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
    student_result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user does not have a student profile"
        )

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
        teacher_result = await db.execute(select(Teacher).where(Teacher.user_id == current_user.id))
        teacher = teacher_result.scalar_one_or_none()
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Current user is not registered as a teacher"
            )

        course_result = await db.execute(select(Course).where(Course.id == session.course_id))
        course = course_result.scalar_one_or_none()
        if not course or course.teacher_id != teacher.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view attendance for this session"
            )

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
