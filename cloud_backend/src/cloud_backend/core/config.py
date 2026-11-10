"""
Application configuration.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    STORAGE_BASE_PATH: str = Field(default=r"D:\Storage")
    JWT_SECRET_KEY: SecretStr = Field(..., min_length=32)
    CORE_DB_URL: SecretStr
    TELEMETRY_DB_URL: SecretStr
    LOG_FILE_PATH: str = "cloud_backend.log"

    @field_validator("STORAGE_BASE_PATH")
    @classmethod
    def resolve_storage_base_path(cls, value: str) -> str:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = BASE_DIR / path
        return str(path.resolve())

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the process-wide validated configuration."""
    return Config()
