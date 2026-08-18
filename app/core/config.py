from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "todo"
    POSTGRES_PASSWORD: str = "todopass"
    POSTGRES_DB: str = "todo"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    BRUTE_FORCE_WINDOW_SECONDS: int = 60
    RATE_LIMIT_GLOBAL_MAX: int = 1000
    MAX_FAILED_ATTEMPTS: int = 20
    REDIS_MAX_CONNECTIONS: int = 5

    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # Dev Mode
    DEV_MODE: bool = False

    # Security
    SECRET_KEY: str = Field(min_length=32, default="THISISSECRETKEYforYourFastAPIApp")
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    ACCESS_TOKEN_EXPIRATION_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRATION_DAYS: int = 30

    # OpenAI Config
    OPENAI_BASE_URL: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL_NAME: str = Field(default="gpt-5.6-luna")

    # Files
    REPORTS_DIR: Path = PROJECT_ROOT / "reports"

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # just using db0 as a best practice
    @computed_field
    @property
    def redis_url(self) -> str:
        """Base Redis URL without database number."""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @computed_field
    @property
    def celery_broker_url(self) -> str:
        """Redis broker URL for Celery (db0)"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @computed_field
    @property
    def celery_backend_url(self) -> str:
        """Redis result backend URL for Celery (db0)"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


setting = Settings()
