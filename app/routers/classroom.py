from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.classroom import Classroom
from app.models.student import Student
from app.models.course import Course
from app.models.class_session import ClassSession
from app.models.teacher import Teacher
from app.models.user import User, Role
from app.dependencies import get_current_admin, get_current_staff, get_current_user
from app.schemas.classroom import (
    ClassroomCreate,
    ClassroomUpdate,
    ClassroomResponse,
    ClassroomDetail,
    EnrollStudentWithRollRequest,
    AssignCourseRequest,
    StudentInClassroom,
    CourseInClassroom,
)
from app.schemas.attendance import ClassSessionResponse
from app.schemas.course import CourseResponse
from app.services.admin_service import assign_course_to_classroom

router = APIRouter()

DBSession = Annotated[AsyncSession, Depends(get_db)]

# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _get_teacher(user_id: int, db: AsyncSession) -> Teacher:
    result = await db.execute(select(Teacher).where(Teacher.user_id == user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a teacher")
    return teacher


async def _verify_teacher_classroom_access(teacher_id: int, classroom_id: int, db: AsyncSession):
    course_check = await db.execute(
        select(Course).where(
            Course.class_id == classroom_id,
            Course.teacher_id == teacher_id,
        )
    )
    if not course_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not teach any course in this classroom",
        )

# ─── Endpoints ────────────────────────────────────────────────────────────────


# ─── ADMIN: Create classroom ────────────────────────────────────────────────

@router.post(
    "/",
    response_model=ClassroomResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a classroom (Admin only)",
)
async def create_classroom(
    data: ClassroomCreate,
    db: DBSession,
    current_user=Depends(get_current_admin),
):
    classroom = Classroom(**data.model_dump())
    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)
    return classroom


# ─── List all classrooms (public/authenticated) ──────────────────────────────

@router.get(
    "/",
    response_model=List[ClassroomResponse],
    summary="List all classrooms",
)
async def list_classrooms(db: DBSession):
    result = await db.execute(select(Classroom))
    return result.scalars().all()


# ─── Get classroom detail ─────────────────────────────────────────────────────

@router.get(
    "/{classroom_id}",
    response_model=ClassroomDetail,
    summary="Get classroom detail with students and courses",
)
async def get_classroom_detail(
    classroom_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Classroom)
        .options(
            joinedload(Classroom.students).joinedload(Student.user),
            joinedload(Classroom.courses).joinedload(Course.teacher).joinedload(Teacher.user),
        )
        .where(Classroom.id == classroom_id)
    )
    classroom = result.unique().scalar_one_or_none()
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    students_data = [
        StudentInClassroom(
            id=s.id,
            student_id=s.student_id,
            roll_no=s.roll_no,
            name=s.user.name,
            email=s.user.email,
            is_active=s.user.is_active,
        )
        for s in classroom.students
    ]
    courses_data = [
        CourseInClassroom(
            id=c.id,
            course_code=c.course_code,
            course_name=c.course_name,
            teacher_name=c.teacher.user.name if c.teacher else None,
        )
        for c in classroom.courses
    ]
    return ClassroomDetail(
        id=classroom.id,
        name=classroom.name,
        section=classroom.section,
        academic_year=classroom.academic_year,
        students=students_data,
        courses=courses_data,
    )


# ─── ADMIN: Update classroom ──────────────────────────────────────────────────

@router.patch(
    "/{classroom_id}",
    response_model=ClassroomResponse,
    summary="Update a classroom (Admin only)",
)
async def update_classroom(
    classroom_id: int,
    data: ClassroomUpdate,
    db: DBSession,
    _=Depends(get_current_admin),
):
    classroom = await db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    for field in ("name", "section", "academic_year"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(classroom, field, value)

    await db.commit()
    await db.refresh(classroom)
    return classroom


# ─── ADMIN: Delete classroom ──────────────────────────────────────────────────

@router.delete(
    "/{classroom_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a classroom (Admin only)",
)
async def delete_classroom(
    classroom_id: int,
    db: DBSession,
    _=Depends(get_current_admin),
):
    classroom = await db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
    await db.delete(classroom)
    await db.commit()


# ─── ADMIN: Enroll student in classroom ─────────────────────────────────────

@router.post(
    "/{classroom_id}/enroll-student",
    response_model=StudentInClassroom,
    summary="Enroll a student into a classroom (Admin only)",
)
async def enroll_student(
    classroom_id: int,
    data: EnrollStudentWithRollRequest,
    db: DBSession,
    _=Depends(get_current_admin),
):
    # Verify classroom
    classroom = await db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    # Find student by student_id (login_id like STU001)
    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))
        .where(Student.student_id == data.student_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    if student.classroom_id == classroom_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this classroom",
        )

    if not student.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll an inactive student"
        )

    student.classroom_id = classroom_id
    if data.roll_no is not None:
        student.roll_no = data.roll_no

    await db.commit()
    await db.refresh(student)

    return StudentInClassroom(
        id=student.id,
        student_id=student.student_id,
        roll_no=student.roll_no,
        name=student.user.name,
        email=student.user.email,
        is_active=student.user.is_active,
    )


# ─── ADMIN: Remove student from classroom ───────────────────────────────────

@router.delete(
    "/{classroom_id}/remove-student/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a student from a classroom (Admin only)",
)
async def remove_student(
    classroom_id: int,
    student_id: str,
    db: DBSession,
    _=Depends(get_current_admin),
):
    result = await db.execute(
        select(Student).where(
            Student.student_id == student_id,
            Student.classroom_id == classroom_id,
        )
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in this classroom",
        )

    student.classroom_id = None
    await db.commit()


# ─── Admin / Teacher: List students in classroom ─────────────────────────────

@router.get(
    "/{classroom_id}/students",
    response_model=List[StudentInClassroom],
    summary="List students in a classroom (Admin or Teacher of this class)",
)
async def list_classroom_students(
    classroom_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff),
):
    # Check classroom exists
    classroom = await db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    # Teachers can only see classrooms they have a course in
    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_classroom_access(teacher.id, classroom_id, db)

    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))
        .where(Student.classroom_id == classroom_id)
    )
    students = result.scalars().all()
    return [
        StudentInClassroom(
            id=s.id,
            student_id=s.student_id,
            roll_no=s.roll_no,
            name=s.user.name,
            email=s.user.email,
            is_active=s.user.is_active,
        )
        for s in students
    ]


# ─── Admin / Teacher: List courses in classroom ───────────────────────────────

@router.get(
    "/{classroom_id}/courses",
    response_model=List[CourseInClassroom],
    summary="List courses in a classroom (Admin or Teacher of this class)",
)
async def list_classroom_courses(
    classroom_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff),
):
    classroom = await db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_classroom_access(teacher.id, classroom_id, db)

    result = await db.execute(
        select(Course)
        .options(joinedload(Course.teacher).joinedload(Teacher.user))
        .where(Course.classroom_id == classroom_id)
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


# ─── Admin / Teacher: List all sessions for a classroom ─────────────────────

@router.get(
    "/{classroom_id}/sessions",
    response_model=List[ClassSessionResponse],
    summary="List all class sessions in a classroom (Admin or Teacher of this class)",
)
async def list_classroom_sessions(
    classroom_id: int,
    db: DBSession,
    current_user: User = Depends(get_current_staff),
):
    classroom = await db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")

    # Get course_ids that belong to this classroom
    courses_result = await db.execute(
        select(Course.id).where(Course.classroom_id == classroom_id)
    )
    course_ids = [row[0] for row in courses_result.all()]

    if current_user.role == Role.teacher:
        teacher = await _get_teacher(current_user.id, db)
        await _verify_teacher_classroom_access(teacher.id, classroom_id, db)
        
        # Only show sessions from this teacher's courses in the classroom
        teacher_courses = await db.execute(
            select(Course.id).where(
                Course.classroom_id == classroom_id,
                Course.teacher_id == teacher.id,
            )
        )
        course_ids = [row[0] for row in teacher_courses.all()]

    sessions_result = await db.execute(
        select(ClassSession).where(ClassSession.course_id.in_(course_ids))
    )
    return sessions_result.scalars().all()


@router.post(
    "/{classroom_id}/assign-course",
    response_model=CourseResponse,
    summary="Assign a course and a teacher to a classroom (Admin only)",
)
async def assign_course(
    classroom_id: int,
    data: AssignCourseRequest,
    db: DBSession,
    _=Depends(get_current_admin),
):
    return await assign_course_to_classroom(db, data.course_id, classroom_id, data.teacher_id)


@router.patch(
    "/{classroom_id}/unassign-course/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unassign a course from a classroom (Admin only)",
)
async def unassign_course(
    classroom_id: int,
    course_id: int,
    db: DBSession,
    _=Depends(get_current_admin),
):
    course = await db.get(Course, course_id)
    if not course or course.classroom_id != classroom_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found in this classroom")
    course.classroom_id = None
    await db.commit()
