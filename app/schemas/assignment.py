from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# ---------- Assignment ----------

class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None


class AssignmentCreate(AssignmentBase):
    course_id: int


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None


class AssignmentOut(AssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime


class AssignmentWithSubmissionCount(AssignmentOut):
    """Optional: useful for teacher dashboard list view."""
    submission_count: int = 0


# ---------- Submission ----------

class SubmissionBase(BaseModel):
    content: Optional[str] = None


class SubmissionCreate(SubmissionBase):
    assignment_id: int
    # file itself comes in as UploadFile in the route, not here


class SubmissionGrade(BaseModel):
    grade: Optional[str] = None
    feedback: Optional[str] = None


class SubmissionOut(SubmissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    student_id: int
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    submitted_at: datetime
    grade: Optional[str] = None
    feedback: Optional[str] = None
    is_graded: bool


class SubmissionWithStudent(SubmissionOut):
    """Optional: useful for teacher viewing all submissions with student info."""
    student_name: Optional[str] = None
    student_email: Optional[str] = None