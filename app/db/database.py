from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

# Use SQLite for prototyping, easy swappable to Postgres
DATABASE_URL = "sqlite+aiosqlite:///./optislot.db"

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency Injection for FastAPI.
    Yields an AsyncSession for the request scope.
    """
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

async def init_db():
    """
    Initializes the database (creates tables).
    Call this on startup.
    """
    from .models import SQLModel
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
