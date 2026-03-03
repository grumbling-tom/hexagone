"""Application settings loaded from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        ENV: The application environment (TEST, DEV, STAGING, PROD).
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENV: Literal["TEST", "DEV", "STAGING", "PROD"] = "DEV"


settings = Settings()
