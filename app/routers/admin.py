# app/routers/admin.py
from fastapi import APIRouter
from app.routers.student import router as student_router
from app.routers.teacher import router as teacher_router
# from app.routers.teacher import router as teacher_router

router = APIRouter(prefix="/admin")

# mount sub-routers under /admin
router.include_router(student_router, prefix="/student", tags=["Admin - Students"])
router.include_router(teacher_router, prefix="/teacher", tags=["Admin - Teachers"])
