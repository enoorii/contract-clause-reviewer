from contextlib import contextmanager
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.orm.session import Session

from app.core.config import setting

# --- ASYNC (for FastAPI) ---
async_engine = create_async_engine(
    setting.ASYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DBSession = Annotated[AsyncSession, Depends(get_db)]

# --- SYNC (for Celery, scripts, etc.) ---
sync_engine = create_engine(
    setting.SYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    class_=Session,
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


@contextmanager
def get_sync_db():
    """Synchronous database session for Celery tasks and scripts."""
    with SyncSessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
