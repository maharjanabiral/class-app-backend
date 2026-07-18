from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, timezone

from app.database import get_db
from app.dependencies import get_current_teacher, get_current_student, get_current_staff, get_current_user
from app.models.user import User
from app.models.course import Course
from app.models.assignment import Assignment, Submission
from app.schemas.assignment import (
    AssignmentBase, AssignmentCreate, AssignmentUpdate, AssignmentOut,
    SubmissionCreate, SubmissionOut, SubmissionGrade, SubmissionWithStudent
)
from app.core.cloudinary import upload_file, delete_file

router = APIRouter(prefix="/courses/{course_id}/assignments", tags=["assignments"])
submission_router = APIRouter(prefix="/assignments", tags=["submissions"])


# ---------- helpers ----------

async def get_course_or_404(course_id: int, db: AsyncSession) -> Course:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


async def get_assignment_or_404(assignment_id: int, db: AsyncSession) -> Assignment:
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


# ---------- Assignment CRUD ----------

@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    course_id: int,
    payload: AssignmentBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    await get_course_or_404(course_id, db)

    assignment = Assignment(
        course_id=course_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.get("", response_model=List[AssignmentOut])
async def list_assignments(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await get_course_or_404(course_id, db)
    result = await db.execute(
        select(Assignment).where(Assignment.course_id == course_id).order_by(Assignment.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{assignment_id}", response_model=AssignmentOut)
async def get_assignment(
    course_id: int,
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = await get_assignment_or_404(assignment_id, db)
    if assignment.course_id != course_id:
        raise HTTPException(status_code=404, detail="Assignment not found in this course")
    return assignment


@router.patch("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment(
    course_id: int,
    assignment_id: int,
    payload: AssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    assignment = await get_assignment_or_404(assignment_id, db)
    if assignment.course_id != course_id:
        raise HTTPException(status_code=404, detail="Assignment not found in this course")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)
    assignment.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    course_id: int,
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    assignment = await get_assignment_or_404(assignment_id, db)
    if assignment.course_id != course_id:
        raise HTTPException(status_code=404, detail="Assignment not found in this course")

    await db.delete(assignment)
    await db.commit()
    return None


# ---------- Submissions ----------

@submission_router.post("/{assignment_id}/submissions", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    assignment_id: int,
    content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    assignment = await get_assignment_or_404(assignment_id, db)

    # check for existing submission (resubmission overwrites)
    result = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()

    file_url = submission.file_url if submission else None
    file_name = submission.file_name if submission else None

    if file:
        file_bytes = await file.read()
        public_id = f"{assignment_id}_{current_user.id}_{file.filename}"
        file_url = await upload_file(file_bytes, filename=public_id, folder="assignments")
        file_name = file.filename

    if submission:
        submission.content = content
        submission.file_url = file_url
        submission.file_name = file_name
        submission.submitted_at = datetime.now(timezone.utc)
        submission.is_graded = False
        submission.grade = None
        submission.feedback = None
    else:
        submission = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            content=content,
            file_url=file_url,
            file_name=file_name,
        )
        db.add(submission)

    await db.commit()
    await db.refresh(submission)
    return submission


@submission_router.get("/{assignment_id}/submissions", response_model=List[SubmissionWithStudent])
async def list_submissions(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff),
):
    await get_assignment_or_404(assignment_id, db)
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.student))
        .where(Submission.assignment_id == assignment_id)
    )
    submissions = result.scalars().all()

    out = []
    for s in submissions:
        item = SubmissionWithStudent.model_validate(s)
        item.student_name = s.student.name if s.student else None
        item.student_email = s.student.email if s.student else None
        out.append(item)
    return out


@submission_router.get("/{assignment_id}/submissions/me", response_model=SubmissionOut)
async def get_my_submission(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_student),
):
    result = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="No submission found")
    return submission


@submission_router.patch("/submissions/{submission_id}/grade", response_model=SubmissionOut)
async def grade_submission(
    submission_id: int,
    payload: SubmissionGrade,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_teacher),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.grade = payload.grade
    submission.feedback = payload.feedback
    submission.is_graded = True

    await db.commit()
    await db.refresh(submission)
    return submission


@submission_router.delete("/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff),
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.file_name:
        public_id = f"{submission.assignment_id}_{submission.student_id}_{submission.file_name}"
        await delete_file(public_id)

    await db.delete(submission)
    await db.commit()
    return None