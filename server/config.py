"""Application configuration."""

import json
import logging
from functools import lru_cache
from typing import Annotated
from urllib.parse import quote

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
    database_ssl_mode: str = "disable"
    cache_host: str = "redis"
    cache_port: int = 6379
    cache_db: int = 0
    cache_username: str | None = None
    cache_password: str | None = None
    cache_use_ssl: bool = False
    cache_ssl_cert_reqs: str = "required"
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
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )
    max_statement_file_size_bytes: int = 10 * 1024 * 1024
    pdf_password_kdf_iterations: int = Field(default=600_000, ge=1)
    statement_download_rate_limit_requests: int = 10
    statement_download_rate_limit_window_seconds: int = 60
    trust_proxy_headers: bool = False
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

    @field_validator("database_ssl_mode")
    @classmethod
    def validate_database_ssl_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"disable", "require"}:
            raise ValueError("database_ssl_mode must be one of: disable, require")
        return normalized

    @field_validator("cache_ssl_cert_reqs")
    @classmethod
    def validate_cache_ssl_cert_reqs(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"none", "optional", "required"}:
            raise ValueError(
                "cache_ssl_cert_reqs must be one of: none, optional, required"
            )
        return normalized

    @property
    def database_url(self) -> str:
        username = quote(self.database_username, safe="")
        password = quote(self.database_password, safe="")
        return (
            "postgresql+asyncpg://"
            f"{username}:{password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_connect_args_async(self) -> dict[str, bool]:
        if self.database_ssl_mode == "require":
            return {"ssl": True}
        return {}

    @property
    def database_url_sync(self) -> str:
        username = quote(self.database_username, safe="")
        password = quote(self.database_password, safe="")
        url = (
            "postgresql+psycopg2://"
            f"{username}:{password}@"
            f"{self.database_host}:{self.database_port}/{self.database_name}"
        )
        if self.database_ssl_mode == "require":
            return f"{url}?sslmode=require"
        return url

    @property
    def redis_url(self) -> str:
        scheme = "rediss" if self.cache_use_ssl else "redis"
        host = self.cache_host
        port = self.cache_port
        db = self.cache_db

        username = quote(self.cache_username or "", safe="")
        password = quote(self.cache_password or "", safe="")
        auth = ""
        if self.cache_username and self.cache_password:
            auth = f"{username}:{password}@"
        elif self.cache_password:
            auth = f":{password}@"
        elif self.cache_username:
            auth = f"{username}@"

        query = ""
        if self.cache_use_ssl:
            query = f"?ssl_cert_reqs={self.cache_ssl_cert_reqs}"

        return f"{scheme}://{auth}{host}:{port}/{db}{query}"

    @property
    def has_wildcard_cors(self) -> bool:
        return "*" in self.cors_allow_origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_logging(level: str) -> None:
    """Configure app logging once."""

    logging.basicConfig(level=level, format="%(levelname)s: %(name)s: %(message)s")
    fastapi_logger.setLevel(level)


settings = get_settings()
