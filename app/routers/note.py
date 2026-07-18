import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, List

from app.database import get_db
from app.models.note import Note
from app.models.course import Course
from app.models.teacher import Teacher
from app.models.student import Student
from app.schemas.note import NoteResponse
from app.dependencies import get_current_teacher, get_current_user
from app.models.user import User

router = APIRouter(prefix="/notes", tags=["Notes"])
DBSession = Annotated[AsyncSession, Depends(get_db)]

UPLOAD_DIR = "uploads/notes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg"}


def save_file(file: UploadFile):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type {ext} not allowed")
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file_path, file.filename


# ── Teacher: upload a note to a course ───────────────────────────────────────
@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a note to a course (Teacher only)",
)
async def upload_note(
    db: DBSession,
    course_id: int = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_teacher),
):
    teacher_result = await db.execute(select(Teacher).where(Teacher.user_id == current_user.id))
    teacher = teacher_result.scalar_one_or_none()

    # Get the specific course this teacher is uploading to, and verify ownership
    course_result = await db.execute(
        select(Course).where(Course.id == course_id, Course.teacher_id == teacher.id)
    )
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or not owned by you")

    file_path, original_filename = save_file(file)

    note = Note(
        title=title,
        file_path=file_path,
        original_filename=original_filename,
        course_id=course.id,
        teacher_id=teacher.id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note

# ── List notes for a course ───────────────────────────────────────────────────
@router.get(
    "/course/{course_id}",
    response_model=List[NoteResponse],
    summary="List notes for a course (enrolled students + teacher)",
)
async def list_notes(
    course_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_user),
):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    teacher_result = await db.execute(select(Teacher).where(Teacher.user_id == current_user.id))
    teacher = teacher_result.scalar_one_or_none()
    is_teacher = teacher is not None and course.teacher_id == teacher.id

    is_enrolled = False
    if not is_teacher:
        student_result = await db.execute(select(Student).where(Student.user_id == current_user.id))
        student = student_result.scalar_one_or_none()
        is_enrolled = student is not None and student.classroom_id == course.classroom_id

    if not is_teacher and not is_enrolled:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(Note)
        .where(Note.course_id == course_id)
        .order_by(Note.created_at.desc())
    )
    return result.scalars().all()


# ── Teacher: list all their own notes ────────────────────────────────────────
@router.get(
    "/my",
    response_model=List[NoteResponse],
    summary="List all notes uploaded by the current teacher",
)
async def my_notes(
    db: DBSession,
    current_user: User = Depends(get_current_teacher),
):
    teacher_result = await db.execute(select(Teacher).where(Teacher.user_id == current_user.id))
    teacher = teacher_result.scalar_one_or_none()

    result = await db.execute(
        select(Note)
        .where(Note.teacher_id == teacher.id)
        .order_by(Note.created_at.desc())
    )
    return result.scalars().all()


# ── Download a note ───────────────────────────────────────────────────────────
@router.get(
    "/{note_id}/download",
    summary="Download a note file (enrolled students + teacher)",
)
async def download_note(
    note_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_user),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    course = await db.get(Course, note.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    teacher_result = await db.execute(select(Teacher).where(Teacher.user_id == current_user.id))
    teacher = teacher_result.scalar_one_or_none()
    is_teacher = teacher is not None and course.teacher_id == teacher.id

    if not is_teacher:
        student_result = await db.execute(select(Student).where(Student.user_id == current_user.id))
        student = student_result.scalar_one_or_none()
        if not student or student.classroom_id != course.classroom_id:
            raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(note.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=note.file_path,
        filename=note.original_filename,
        media_type="application/octet-stream",
    )


# ── Teacher: delete their own note ────────────────────────────────────────────
@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note (Teacher only, must be owner)",
)
async def delete_note(
    note_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_teacher),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    teacher_result = await db.execute(select(Teacher).where(Teacher.user_id == current_user.id))
    teacher = teacher_result.scalar_one_or_none()

    if note.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="You can only delete your own notes")

    if os.path.exists(note.file_path):
        os.remove(note.file_path)

    await db.delete(note)
    await db.commit()
