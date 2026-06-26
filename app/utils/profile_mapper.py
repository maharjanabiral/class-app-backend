from app.models import User, Role
from app.schemas.user import UserProfileOut


def build_profile(user: User) -> UserProfileOut:
    if user.role == Role.student and user.student:
        classroom = user.student.classroom

        return UserProfileOut(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            classroom=classroom,
            courses=classroom.courses if classroom else [],
        )

    if user.role == Role.teacher and user.teacher:
        return UserProfileOut(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            courses=user.teacher.courses,
        )

    return UserProfileOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )
