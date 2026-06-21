from fastapi import APIRouter
from app.routers.student import router as student_router
from app.routers.teacher import router as teacher_router
from app.routers.course import router as course_router
from app.routers.classroom import router as classroom_router

router = APIRouter(prefix="/admin")

# mount sub-routers under /admin
router.include_router(student_router, prefix="/students", tags=["Admin - Students"])
router.include_router(teacher_router, prefix="/teachers", tags=["Admin - Teachers"])
router.include_router(course_router, prefix="/courses", tags=["Admin - Courses"])
router.include_router(classroom_router, prefix="/classrooms", tags=["Admin - Classrooms"])
