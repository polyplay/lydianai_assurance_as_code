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
    https_required: bool = Field(default=False, alias="AAC_HTTPS_REQUIRED")
    upload_dir: str = Field(default="var/uploads", alias="AAC_UPLOAD_DIR")
    cors_origins: str = Field(default="", alias="AAC_CORS_ORIGINS")
    max_import_bytes: int = Field(default=50 * 1024 * 1024, alias="AAC_MAX_IMPORT_BYTES")
    max_evidence_bytes: int = Field(default=50 * 1024 * 1024, alias="AAC_MAX_EVIDENCE_BYTES")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_runtime_configuration(self) -> None:
        if self.environment.lower() != "production":
            return
        if (
            self.jwt_secret == "change-me-change-me-change-me-change-me"
            or len(self.jwt_secret) < 32
        ):
            raise RuntimeError("AAC_JWT_SECRET must be a non-default secret of at least 32 characters")
        if not self.secret_encryption_key or len(self.secret_encryption_key) < 32:
            raise RuntimeError("AAC_SECRET_ENCRYPTION_KEY must be at least 32 characters")
        if not self.https_required:
            raise RuntimeError("AAC_HTTPS_REQUIRED must be true in production")
        if "*" in self.allowed_cors_origins:
            raise RuntimeError("Wildcard CORS origins are prohibited in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
