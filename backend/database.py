"""Database setup — async SQLAlchemy + SQLite."""

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings


def _ensure_db_dir() -> str:
    """Ensure database directory exists and return the URL."""
    url = settings.database_url
    if url.startswith("sqlite"):
        # Extract path from sqlite+aiosqlite:///data/onyx.db or sqlite:///path
        prefix = "sqlite+aiosqlite:///" if "+aiosqlite" in url else "sqlite:///"
        path = url[len(prefix):] if url.startswith(prefix) else url
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    return url


engine = create_async_engine(
    _ensure_db_dir(),
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def init_db():
    """Create all tables."""
    from .models import Base  # noqa: F401 — registers models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
