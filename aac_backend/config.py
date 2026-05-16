from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://aac:aac@localhost:5432/aac",
        alias="AAC_DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="AAC_REDIS_URL")
    jwt_secret: str = Field(default="change-me-change-me-change-me-change-me", alias="AAC_JWT_SECRET")
    jwt_expiry_hours: int = Field(default=8, alias="AAC_JWT_EXPIRY_HOURS")
    secret_encryption_key: str | None = Field(default=None, alias="AAC_SECRET_ENCRYPTION_KEY")
    github_api_base_url: str = Field(default="https://api.github.com", alias="AAC_GITHUB_API_BASE_URL")
    environment: str = Field(default="development", alias="AAC_ENVIRONMENT")
    upload_dir: str = Field(default="var/uploads", alias="AAC_UPLOAD_DIR")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
