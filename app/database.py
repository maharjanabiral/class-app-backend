from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings
import ssl

ssl_context = ssl.create_default_context()

engine = create_async_engine(settings.DATABASE_URL, echo=True, connect_args={"ssl": ssl_context})

# pyrefly: ignore [no-matching-overload]
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

