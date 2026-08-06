from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    POSTGRES_USER: str = "todo"
    POSTGRES_PASSWORD: str = "todopass"
    POSTGRES_DB: str = "todo"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"

    DEV_MODE: bool = False
    DEFAULT_PER_PAGE: int = 10

    SECRET_KEY: str = "secretkey"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    ACCESS_TOKEN_EXPIRATION_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRATION_DAYS: int = 30

    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # Fixed: Added @ and :port
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        # Fixed: Added @ and :port
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


setting = Settings()
