from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import async_engine
from app.infrastructure.logging import setup_logging, shutdown_logging
from app.middleware.request_logging import RequestLogMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize async logging
    print("🚀 Setting up async logging...")
    setup_logging()
    print("✅ Async logging initialized")

    yield

    # Shutdown: Flush and stop
    print("🔄 Shutting down logging...")
    shutdown_logging()
    print("✅ Logging shutdown complete")
    print("🔄 Disonnecting database...")
    await async_engine.dispose()
    print("✅ Database disconnected")


app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestLogMiddleware)


def main():
    print("Hello from contract-clause-reviewer!")


if __name__ == "__main__":
    main()
