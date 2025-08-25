"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "PathPal API"
    VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str

    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # External APIs
    OPENAI_API_KEY: str
    MAPBOX_API_KEY: str

    # Email/SMTP Configuration for Emergency Alerts
    SMTP_USERNAME: str = "test@example.com"
    SMTP_PASSWORD: str = "test-password"
    SMTP_FROM_EMAIL: str = "test@example.com"
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_STARTTLS: bool = True
    SMTP_SSL_TLS: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


settings = get_settings()
