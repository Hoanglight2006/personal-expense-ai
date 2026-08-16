from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    CORS_ORIGINS: list[str] = Field(default_factory=list)

    # ---- File Uploads & External Services ----
    MAX_IMAGE_SIZE_MB: int = 10
    MAX_EXCEL_SIZE_MB: int = 5
    OCR_PROVIDER: str = "gemini"  # 'local', 'gemini', or 'none' for fallback
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    model_config = {"env_file": Path(__file__).resolve().parents[1] / ".env"}


settings = Settings()
