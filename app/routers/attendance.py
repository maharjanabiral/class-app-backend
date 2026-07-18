import io
import csv
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse

from sqlalchemy import func 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from datetime import datetime, timezone

from app.services import livekit_service
from app.database import get_db
from app.dependencies import get_current_student, get_current_staff, get_current_user
from app.models.user import User, Role
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.course import Course
from app.models.class_session import ClassSession
from app.models.session_participant import SessionParticipant
from app.models.attendance_record import AttendanceRecord
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

# @router.get(
#     "/sessions",
#     response_model=List[ClassSessionResponse],
#     summary="List sessions (Teacher: their own courses; Admin: optionally filter by course_id)",
# )
# async def list_sessions(
#     db: DBSession,
#     course_id: Optional[int] = Query(default=None, description="Filter by course ID"),
#     current_user: User = Depends(get_current_staff),
# ):
#     if current_user.role == Role.teacher:
#         teacher = await _get_teacher(current_user.id, db)
#         # Get course IDs for this teacher
#         courses_q = select(Course.id).where(Course.teacher_id == teacher.id)
#         if course_id is not None:
#             courses_q = courses_q.where(Course.id == course_id)
#
#         course_ids_result = await db.execute(courses_q)
#         course_ids = [row[0] for row in course_ids_result.all()]
#
#         if not course_ids:
#             return []
#
#         query = select(ClassSession).where(ClassSession.course_id.in_(course_ids))
#     else:
#         # Admin
#         query = select(ClassSession)
#         if course_id is not None:
#             query = query.where(ClassSession.course_id == course_id)
#
#     result = await db.execute(query)
#     return result.scalars().all()


@router.get("/sessions", summary="List sessions")
async def list_sessions(
    db: DBSession,
    course_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_staff),
):
    query = (
        select(
            ClassSession,
            func.count(AttendanceRecord.id.distinct()).label("total_present"),
            func.count(Student.id.distinct()).label("total_students"),
        )
        .join(Course, Course.id == ClassSession.course_id)
        .outerjoin(Student, Student.classroom_id == Course.classroom_id)
        .outerjoin(AttendanceRecord, AttendanceRecord.session_id == ClassSession.id)
        .group_by(ClassSession.id)
    )

    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        courses_q = select(Course.id).where(Course.teacher_id == teacher.id)
        if course_id is not None:
            courses_q = courses_q.where(Course.id == course_id)
        course_ids_result = await db.execute(courses_q)
        course_ids = [row[0] for row in course_ids_result.all()]
        if not course_ids:
            return []
        query = query.where(ClassSession.course_id.in_(course_ids))
    else:
        if course_id is not None:
            query = query.where(ClassSession.course_id == course_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": s.id,
            "course_id": s.course_id,
            "title": s.title,
            "is_active": s.is_active,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "created_at": s.created_at,
            "total_present": total_present,
            "total_students": total_students,
        }
        for s, total_present, total_students in rows
    ]

@router.get(
    "/sessions/active",
    response_model=ClassSessionResponse,
    summary="Get the active session for the logged-in student's class",
)
async def get_active_session_for_student(
    db: DBSession,
    current_user: User = Depends(get_current_student),
):
    student = await _get_student(current_user.id, db)

    courses_result = await db.execute(
        select(Course).where(Course.classroom_id == student.classroom_id)
    )
    courses = courses_result.scalars().all()
    if not courses:
        raise HTTPException(status_code=404, detail="No courses found for your class")

    course_ids = [c.id for c in courses]

    result = await db.execute(
        select(ClassSession).where(
            ClassSession.course_id.in_(course_ids),
            ClassSession.is_active == True
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="No active session found for your class")

    return session

@router.get("/sessions/{session_id}", response_model=ClassSessionResponse)
async def get_session(
    session_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff),
):
    result = await db.execute(select(ClassSession).where(ClassSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_session_access(teacher.id, session, db)
    return session


# ─── NEW: Student — view their own attendance records ────────────────────────

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

@router.post("/sessions/{session_id}/join", status_code=200)
async def join_session(session_id: int, db: DBSession, current_user: User = Depends(get_current_student)):
    student = await _get_student(current_user.id, db)

    session_result = await db.execute(select(ClassSession).where(ClassSession.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is not active")

    course_result = await db.execute(select(Course).where(Course.id == session.course_id))
    course = course_result.scalar_one_or_none()
    if student.classroom_id != course.classroom_id:
        raise HTTPException(status_code=403, detail="You do not belong to this class")

    existing = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.student_id == student.id
        )
    )
    already_joined = existing.scalar_one_or_none()

    if not already_joined:
        db.add(SessionParticipant(session_id=session_id, student_id=student.id))
        await db.commit()

    response = {"detail": "Joined session" if not already_joined else "Rejoined session"}

    if session.room_name:
        creds = livekit_service.generate_student_token(
            room_name=session.room_name,
            user_id=current_user.id,
            display_name=current_user.name,
        )
        response["livekit"] = {
            "token": creds.token,
            "ws_url": creds.ws_url,
            "room_name": creds.room_name,
        }

    return response


@router.post("/sessions/{session_id}/leave", status_code=200)
async def leave_session(session_id: int, db: DBSession, current_user: User = Depends(get_current_student)):
    student = await _get_student(current_user.id, db)

    result = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.student_id == student.id
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=400, detail="You have not joined this session")

    await db.delete(participant)
    await db.commit()
    return {"detail": "Left session"}

@router.post(
    "/sessions/{session_id}/end",
    response_model=ClassSessionResponse,
    summary="End a class session",
)
async def end_session(
    session_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff),
):
    result = await db.execute(select(ClassSession).where(ClassSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
 
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_session_access(teacher.id, session, db)
 
    if not session.is_active:
        raise HTTPException(status_code=400, detail="Session is not active")
 
    participants_result = await db.execute(
        select(SessionParticipant).where(SessionParticipant.session_id == session.id)
    )
    participants = participants_result.scalars().all()
 
    for p in participants:
        existing = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.session_id == session.id,
                AttendanceRecord.student_id == p.student_id
            )
        )
        if not existing.scalar_one_or_none():
            db.add(AttendanceRecord(session_id=session.id, student_id=p.student_id))
 
    if session.room_name:
        try:
            await livekit_service.delete_room(session.room_name)
        except Exception as e:
            print(f"[livekit] room teardown failed for session {session.id}: {e}")
        session.room_status = "ended"
 
    session.is_active = False
    session.ended_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session

@router.post(
    "/courses/{course_id}/start",
    response_model=ClassSessionResponse,
    summary="Start attendance for a course"
)
async def start_attendance(
    course_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff),
):
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_course_access(teacher.id, course_id, db)
    else:
        course_result = await db.execute(select(Course).where(Course.id == course_id))
        if not course_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Course not found")
 
    active_result = await db.execute(
        select(ClassSession).where(
            ClassSession.course_id == course_id,
            ClassSession.is_active == True
        )
    )
    if active_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An attendance session is already active for this course")
 
    now = datetime.now(timezone.utc)
    session = ClassSession(
        course_id=course_id,
        title=f"Attendance {now:%Y-%m-%d}",
        is_active=True,
        started_at=now,
    )
    db.add(session)
    await db.flush()  # get session.id before commit so we can name the room
 
    room_name = f"session-{session.id}"
    try:
        await livekit_service.create_room(room_name)
    except Exception as e:
        # Don't let a LiveKit outage block attendance tracking entirely —
        # the session can still exist without a live room; log and continue.
        # Swap for your logger of choice.
        print(f"[livekit] room creation failed for session {session.id}: {e}")
        room_name = None
 
    session.room_name = room_name
    session.room_status = "live" if room_name else "not_started"
 
    await db.commit()
    await db.refresh(session)
    return session



# ─── NEW: teacher join endpoint (admin grants, doesn't touch attendance) ─────
 
@router.post("/sessions/{session_id}/join-as-host", status_code=200)
async def join_session_as_host(
    session_id: int, db: DBSession, current_user: User = Depends(get_current_staff)
):
    result = await db.execute(select(ClassSession).where(ClassSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
 
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_session_access(teacher.id, session, db)
 
    if not session.room_name:
        raise HTTPException(status_code=400, detail="This session has no live room")
 
    creds = livekit_service.generate_teacher_token(
        room_name=session.room_name,
        user_id=current_user.id,
        display_name=current_user.name,
    )
    return {"livekit": {"token": creds.token, "ws_url": creds.ws_url, "room_name": creds.room_name}}


@router.post("/livekit/webhook", include_in_schema=False)
async def livekit_webhook(request: Request, db: DBSession):
    body = await request.body()
    auth_header = request.headers.get("Authorization", "")
 
    receiver = lk_api.WebhookReceiver(
        livekit_service.LIVEKIT_API_KEY, livekit_service.LIVEKIT_API_SECRET
    )
    try:
        event = receiver.receive(body, auth_header)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
 
    room_name = event.room.name if event.room else None
    if not room_name or not room_name.startswith("session-"):
        return {"ok": True}  # not one of ours
 
    try:
        session_id = int(room_name.removeprefix("session-"))
    except ValueError:
        return {"ok": True}
 
    session_result = await db.execute(select(ClassSession).where(ClassSession.id == session_id))
    session = session_result.scalar_one_or_none()
    if not session:
        return {"ok": True}
 
    identity = event.participant.identity if event.participant else None
    if not identity:
        return {"ok": True}
 
    try:
        user_id = int(identity)
    except ValueError:
        return {"ok": True}
 
    if event.event == "participant_joined":
        student_result = await db.execute(select(Student).where(Student.user_id == user_id))
        student = student_result.scalar_one_or_none()
        if student:
            existing = await db.execute(
                select(SessionParticipant).where(
                    SessionParticipant.session_id == session.id,
                    SessionParticipant.student_id == student.id,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(SessionParticipant(session_id=session.id, student_id=student.id))
                await db.commit()
 
    elif event.event == "egress_ended":
        # Recording finished — event.egress_info has the file location
        if event.egress_info and event.egress_info.file_results:
            file_result = event.egress_info.file_results[0]
            session.recording_url = file_result.location
            session.recording_status = "completed"
            await db.commit()
 
    return {"ok": True}
