# app/main.py - Ensure this is correct

from contextlib import asynccontextmanager

from fastapi import FastAPI

# from sqlmodel.ext.asyncio.session import AsyncSession
from app.api.auth import router as auth_router
from app.api.users import router as user_router
from app.db.database import async_engine

# from app.db.seed import seed_admin_user
from app.infrastructure.logging import setup_logging, shutdown_logging
from app.infrastructure.redis.client import redis_client
from app.middleware.request_logging import RequestLogMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize async logging
    print("🚀 Setting up async logging...")
    setup_logging()
    print("✅ Async logging initialized")

    # async with AsyncSession(async_engine) as db:
    #     await seed_admin_user(db=db)

    yield
    await redis_client.aclose(close_connection_pool=True)
    # Shutdown: Flush and stop
    print("🔄 Shutting down logging...")
    shutdown_logging()
    print("✅ Logging shutdown complete")
    print("🔄 Disonnecting database...")
    await async_engine.dispose()
    print("✅ Database disconnected")


# Create app instance
app = FastAPI(lifespan=lifespan)

# Register routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")


# Add health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "Service is running"}


# Add middleware
app.add_middleware(RequestLogMiddleware)
