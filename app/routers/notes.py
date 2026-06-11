from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
import os
from datetime import datetime

from app.database import get_db
from app.dependencies import get_teacher_profile, get_student_profile
from app.models.note import Note
from app.models.classcourse import ClassCourse
from app.schemas.note import NoteResponse

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post("/", response_model=NoteResponse)
async def upload_note(
    title: str = Form(...),
    description: str = Form(None),
    class_course_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_teacher=Depends(get_teacher_profile)
):
    print(current_teacher.id)
    result = await db.execute(
        select(ClassCourse).where(
            ClassCourse.id == class_course_id,
            ClassCourse.teacher_id == current_teacher.id
        )
    )
    class_course = result.scalar_one_or_none()

    if not class_course:
        raise HTTPException(
            status_code=403,
            detail="Not allowed to upload for this class/course"
        )

    upload_dir = "uploads/notes"
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    note = Note(
        title=title,
        description=description,
        file_name=file.filename,
        file_path=file_path,
        class_course_id=class_course_id
    )

    db.add(note)
    await db.commit()
    result = await db.execute(
        select(Note)
        .options(joinedload(Note.class_course))
        .where(Note.id == note.id)
    )

    note = result.scalar_one()

    return note


@router.get("/me", response_model=list[NoteResponse])
async def get_my_notes(
    db: AsyncSession = Depends(get_db),
    current_student=Depends(get_student_profile)
):
    result = await db.execute(
        select(Note)
        .join(ClassCourse)
        .options(joinedload(Note.class_course))
        .where(ClassCourse.class_id == current_student.classroom_id)
        .order_by(Note.created_at.desc())
    )

    return result.scalars().all()


@router.get("/course/{course_id}", response_model=list[NoteResponse])
async def get_notes_by_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_student=Depends(get_student_profile)
):
    result = await db.execute(
        select(Note)
        .join(ClassCourse)
        .options(joinedload(Note.class_course))
        .where(
            ClassCourse.class_id == current_student.classroom_id,
            ClassCourse.course_id == course_id
        )
        .order_by(Note.created_at.desc())
    )

    return result.scalars().all()


@router.get("/teacher", response_model=list[NoteResponse])
async def teacher_notes(
    db: AsyncSession = Depends(get_db),
    current_teacher=Depends(get_teacher_profile)
):
    result = await db.execute(
        select(Note)
        .join(ClassCourse)
        .options(joinedload(Note.class_course))
        .where(ClassCourse.teacher_id == current_teacher.id)
        .order_by(Note.created_at.desc())
    )

    return result.scalars().all()


@router.get("/download/{note_id}")
async def download_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_student_profile)
):
    result = await db.execute(
        select(Note).where(Note.id == note_id)
    )

    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return FileResponse(
        path=note.file_path,
        filename=note.file_name,
        media_type="application/octet-stream"
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_teacher=Depends(get_teacher_profile)
):
    result = await db.execute(
        select(Note)
        .join(ClassCourse)
        .where(
            Note.id == note_id,
            ClassCourse.teacher_id == current_teacher.id
        )
    )

    note = result.scalar_one_or_none()

    if not note:
        raise HTTPException(status_code=404, detail="Not found")

    await db.delete(note)
    await db.commit()

    return {"message": "Note deleted successfully"}
