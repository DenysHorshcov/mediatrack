from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: SecretStr | None = None
    test_database_url: SecretStr | None = None

    jwt_secret: SecretStr = SecretStr(
        "dev-insecure-change-me-must-be-at-least-32-bytes"
    )
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 7 * 24 * 60

    session_cookie_name: str = "mediatrack_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"

    frontend_origin: str = "http://localhost:5173"

    tmdb_api_key: SecretStr | None = None
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p/w342"
    tmdb_language: str = "uk-UA"
    tmdb_timeout_seconds: float = 8.0

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def normalize_empty_url(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("database_url", "test_database_url")
    @classmethod
    def validate_postgresql_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        try:
            url = make_url(value.get_secret_value())
        except (ArgumentError, ValueError):
            raise ValueError("Expected a valid PostgreSQL connection URL") from None
        if url.drivername not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError("Only PostgreSQL with the Psycopg driver is supported")
        if not url.host or not url.database:
            raise ValueError("PostgreSQL URL must include a host and database name")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
