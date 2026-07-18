from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import engine, Base
# Import all models to ensure they register on the Base metadata
import app.models # noqa: F401
from fastapi.security import HTTPBearer
from app.routers import auth, admin, classroom, attendance, teacher_self, student_self, course, notice, note, profile, assignment


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

security = HTTPBearer()
app = FastAPI(title="ClassPlus API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(admin.router)
app.include_router(teacher_self.router, prefix="/teacher")
app.include_router(student_self.router, prefix="/student")
app.include_router(attendance.router)
app.include_router(notice.router)
app.include_router(note.router)
app.include_router(assignment.router)
app.include_router(assignment.submission_router)
# app.include_router(course.router)
# TODO: course.router is imported above but was never registered here — found while wiring up
# assignment routes (15 Jul). Unclear if this is intentional or a bug; if course/classroom
# endpoints are returning 404 in the frontend, this is likely why. Check with teammate before
# enabling, in case course routes were deliberately moved elsewhere or merged into another router.

@app.get("/")
async def root():
    return {"message": "ClassPlus API is running"}
