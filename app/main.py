from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="ClassPlus API", version="1.0.0", lifespan=lifespan)

app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "ClassPlus API is running"}
