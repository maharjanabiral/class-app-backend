from sqlalchemy import text
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base
# Import all models to ensure they register on the Base metadata
import app.models # noqa: F401
from fastapi.security import HTTPBearer
from app.routers import auth, admin, classroom, attendance, teacher_self, student_self, course

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # await conn.execute(text("DROP SCHEMA public CASCADE"))
        # await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    yield

security = HTTPBearer()
app = FastAPI(title="ClassPlus API", version="1.0.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(classroom.router)
app.include_router(admin.router)
app.include_router(course.router)
app.include_router(teacher_self.router, prefix="/teacher")
app.include_router(student_self.router, prefix="/student")
app.include_router(attendance.router)

@app.get("/")
async def root():
    return {"message": "ClassPlus API is running"}
