"""Application settings loaded from environment variables."""

from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse, urlunparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        ENV: The application environment (TEST, DEV, STAGING, PROD).
        DATABASE_URL: The database connection URL.
        DEFAULT_PAGE_SIZE: Default number of items per page for pagination.
    """

    model_config = SettingsConfigDict(
        env_file=".env.development", env_file_encoding="utf-8", extra="ignore"
    )

    ENV: Literal["TEST", "DEV", "STAGING", "PROD"] = "DEV"
    DATABASE_URL: str = ""
    DEFAULT_PAGE_SIZE: int = 20
    SESSION_COOKIE_NAME: str = "sessionid"
    SESSION_EXPIRY_HOURS: int = 24

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    HEXAGONE_AWS_REGION: str = "eu-west-1"
    HEXAGONE_S3_BUCKET: str = "hexagone-gpx-uploads"
    HEXAGONE_S3_ENDPOINT_URL: str | None = None
    PRESIGNED_URL_EXPIRY_SECONDS: int = 300
    PRESIGNED_GET_URL_EXPIRY_SECONDS: int = 60 * 60  # 1 hour
    PRESIGNED_PUT_URL_EXPIRY_SECONDS: int = 5 * 60  # 5 minutes

    H3_RESOLUTION: int = 10
    MAX_GPX_BYTES: int = 10 * 1024 * 1024
    MAX_GPX_POINTS: int = 200_000
    MAX_GPX_POLYGONS: int = 1_000
    MAX_GPX_CELLS: int = 100_000

    GIT_SHA: str = "unknown"

    @property
    def session_expiry_seconds(self) -> int:
        """Compute session expiry in seconds from hours."""
        return self.SESSION_EXPIRY_HOURS * 3600

    @model_validator(mode="before")
    @classmethod
    def validate_database_url(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Validate and set default DATABASE_URL for DEV environment.

        For PROD and STAGING environments, ensures PostgreSQL connections use SSL
        and URL-encodes credentials to handle special characters.

        Returns:
            The validated Settings instance.

        Raises:
            ValueError: If DATABASE_URL is not provided in non-DEV environments.
        """
        database_url: str = data.get("DATABASE_URL", "")
        env = data.get("ENV", "DEV")

        # Process PostgreSQL URLs in PROD/STAGING environments
        if database_url and env in ("PROD", "STAGING"):
            parsed = urlparse(database_url)

            if (
                not parsed.username
                or not parsed.password
                or not parsed.hostname
                or not parsed.port
            ):
                msg = (
                    "DATABASE_URL must include username, password, hostname, and port "
                    "for PROD/STAGING environments"
                )
                raise ValueError(msg)

            # URL-encode username and password to handle special characters
            encoded_username = quote_plus(parsed.username)
            encoded_password = quote_plus(parsed.password)
            encoded_netloc = (
                f"{encoded_username}:{encoded_password}@{parsed.hostname}:{parsed.port}"
            )

            # Parse and update query parameters
            query_params = parse_qs(parsed.query)

            # Add sslmode=require if not already present
            if "sslmode" not in query_params:
                query_params["sslmode"] = ["require"]

            # Reconstruct URL with encoded credentials and updated query parameters
            new_query = urlencode(query_params, doseq=True)
            data["DATABASE_URL"] = urlunparse(
                (
                    parsed.scheme,
                    encoded_netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment,
                )
            )
            return data

        if database_url != "":
            return data

        if env in {"DEV", "TEST"}:
            # FIXME: Kinda grim hard-coding, but Good Enough™.
            backend_dir = Path(__file__).resolve().parent.parent.parent
            data["DATABASE_URL"] = f"sqlite:///{backend_dir / 'sqlite.db'}"
            return data

        msg = f"DATABASE_URL must be provided when ENV is '{env}'"
        raise ValueError(msg)

    @model_validator(mode="after")
    def check_aws_credentials(self: Settings) -> Settings:
        if self.ENV == "DEV" and (
            not self.AWS_ACCESS_KEY_ID or not self.AWS_SECRET_ACCESS_KEY
        ):
            msg = (
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set "
                "in DEV (for LocalStack)."
            )
            raise ValueError(msg)

        return self


settings = Settings()
