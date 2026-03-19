"""Application configuration."""

import json
import logging
from functools import lru_cache
from typing import Annotated

from fastapi.logger import logger as fastapi_logger
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    debug: bool = False
    database_name: str = "fastapi-app"
    database_username: str = "postgres"
    database_password: str = "postgres"
    database_host: str = "db"
    database_port: int = 5432
    cache_host: str = "redis"
    cache_port: int = 6379
    cache_db: int = 0
    storage_provider: str = "local"
    storage_bucket_name: str | None = None
    storage_prefix: str = "statements"
    statement_storage_dir: str = "storage/statements"
    statement_api_key: str | None = None
    aws_region: str = "af-south-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    azure_storage_connection_string: str | None = None
    azure_storage_account_url: str | None = None
    azure_storage_account_key: str | None = None
    azure_storage_container: str | None = None
    minio_endpoint_url: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_secure: bool = True
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["*"]
    )
    log_level: str = "INFO"
    enable_debug_toolbar: bool = False

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return ["*"]
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return ["*"]

    @property
    def database_url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.database_username}:{self.database_password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            "postgresql+psycopg2://"
            f"{self.database_username}:{self.database_password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.cache_host}:{self.cache_port}/{self.cache_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging(level: str) -> None:
    """Configure app logging once."""

    logging.basicConfig(level=level, format="%(levelname)s: %(name)s: %(message)s")
    fastapi_logger.setLevel(level)


settings = get_settings()
