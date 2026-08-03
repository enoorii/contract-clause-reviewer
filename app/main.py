from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import async_engine
from app.api.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown
    await async_engine.dispose()

tags_metadta = [
    {"name": "auth", "description": "authentication endpoints"},
]

app = FastAPI(title="to-do-app", lifespan=lifespan, openapi_tags=tags_metadta)
app.include_router(auth_router, tags=["auth"])

app = FastAPI(title="contract-clause-reviewer", lifespan=lifespan)

app.include_router