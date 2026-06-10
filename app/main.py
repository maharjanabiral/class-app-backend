from sqlalchemy import text
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import auth, admin
from fastapi.security import HTTPBearer


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
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"message": "ClassPlus API is running"}
