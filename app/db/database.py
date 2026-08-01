from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import setting

async_engine = create_async_engine(
    setting.ASYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,
)


AssyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db():
    async with AssyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise


DBSession = Annotated[AsyncSession, Depends(get_db)]
