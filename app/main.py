from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown
    await async_engine.dispose()


app = FastAPI()

app = FastAPI(title="contract-clause-reviewer", lifespan=lifespan)
