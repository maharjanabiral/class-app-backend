from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base
# Import all models to ensure they register on the Base metadata
import app.models
from app.routers import auth, classroom, student, teacher, attendance

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="ClassPlus API", version="1.0.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(classroom.router)
app.include_router(student.router)
app.include_router(teacher.router)
app.include_router(attendance.router)

@app.get("/")
async def root():
    return {"message": "ClassPlus API is running"}
