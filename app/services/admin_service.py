from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User, Role
from app.models.student import Student
from app.models.teacher import Teacher
from app.schemas.student import StudentCreate
from app.schemas.teacher import TeacherCreate
from app.core.security import generate_default_password, hash_password


async def _generate_login_id(db: AsyncSession, role: Role) -> str:
    if role == Role.student:
        prefix = "STU"
        result = await db.execute(select(func.count()).select_from(Student))
    else:
        prefix = "TCH"
        result = await db.execute(select(func.count()).select_from(Teacher))

    count = result.scalar()
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
