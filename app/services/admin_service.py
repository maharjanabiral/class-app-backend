from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from app.models.user import User, Role
from app.models.student import Student
from app.models.teacher import Teacher
from app.schemas.student import StudentCreate
from app.schemas.teacher import TeacherCreate
from app.core.security import generate_default_password, hash_password
from app.models.course import Course
from app.models.classroom import Classroom
from fastapi import HTTPException, status


async def _generate_login_id(db: AsyncSession, role: Role) -> str:
    if role == Role.student:
        prefix = "STU"
        result = await db.execute(select(func.count()).select_from(Student))
    else:
        prefix = "TCH"
        result = await db.execute(select(func.count()).select_from(Teacher))

    count = result.scalar() or 0
    return f"{prefix}{str(count + 1).zfill(3)}"


async def create_student(db: AsyncSession, data: StudentCreate) -> dict:
    login_id = await _generate_login_id(db, Role.student)
    default_password = generate_default_password(data.name, login_id)
    hashed = hash_password(default_password)

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hashed,
        role=Role.student,
        login_id=login_id,
        is_created_by_admin=True,
    )
    db.add(user)
    await db.flush()  # get user.id without full commit

    student = Student(
        student_id=login_id,
        user_id=user.id,
        phone=data.phone,
        roll_no=data.roll_no,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    await db.refresh(user)  # ensure user fields are loaded after commit

    return {
        "student_id": login_id,
        "default_password": default_password,
        "user": user,
    }


async def create_teacher(db: AsyncSession, data: TeacherCreate) -> dict:
    login_id = await _generate_login_id(db, Role.teacher)
    default_password = generate_default_password(data.name, login_id)
    hashed = hash_password(default_password)

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hashed,
        role=Role.teacher,
        login_id=login_id,
        is_created_by_admin=True,
    )
    db.add(user)
    await db.flush()

    teacher = Teacher(
        teacher_id=login_id,
        user_id=user.id,
        department=data.department,
        phone=data.phone,
    )
    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)
    await db.refresh(user)

    return {
        "teacher_id": login_id,
        "default_password": default_password,
        "user": user,
    }


async def assign_course_to_classroom(
    db: AsyncSession,
    course_id: int,
    classroom_id: int,
    teacher_id: int | None = None) -> Course:
    classroom = await db.get(Classroom, classroom_id)
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if teacher_id is not None:
        teacher = await db.get(Teacher, teacher_id)
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Teacher not found"
            )
        course.teacher_id = teacher_id  # type: ignore

    course.classroom_id = classroom_id  # type: ignore
    await db.commit()
    await db.refresh(course)
    return course


async def enroll_students_in_course(
    db: AsyncSession,
    course_id: int,
    student_login_ids: List[str]
) -> List[Student]:
    # Fetch course with current students
    result = await db.execute(
        select(Course).options(joinedload(Course.students)).where(Course.id == course_id)
    )
    course = result.unique().scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Fetch students by login_id
    student_result = await db.execute(
        select(Student).where(Student.student_id.in_(student_login_ids))
    )
    students = student_result.scalars().all()

    if len(students) != len(student_login_ids):
        found = {s.student_id for s in students}
        missing = [sid for sid in student_login_ids if sid not in found]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Students not found: {missing}"
        )

    course.students.extend([s for s in students if s not in course.students])
    await db.commit()
    return course.students
