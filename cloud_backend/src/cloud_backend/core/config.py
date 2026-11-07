"""
Application configuration.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class Config(BaseSettings):
    """
    Application configuration class.
    """

    STORAGE_BASE_PATH: str
    JWT_SECRET_KEY: SecretStr = Field(..., min_length=32, max_length=32)
    CORE_DB_URL: SecretStr
    TELEMETRY_DB_URL: SecretStr
    LOG_FILE_PATH: str

    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
    )


@lru_cache
def get_config() -> Config:
    """
    Returns the application configuration.
    """
    return Config()
