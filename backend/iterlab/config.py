"""Application configuration.

All settings are read from environment variables prefixed with ``ITERLAB_``.
A ``.env`` file at the repo root (or CWD) is loaded automatically for local dev.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ITERLAB_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- environment ------------------------------------------------------
    env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    # -- security -------------------------------------------------------
    jwt_secret: str = Field(min_length=1)
    jwt_algorithm: str = "HS256"
    access_token_ttl: int = 900  # seconds
    refresh_token_ttl: int = 60 * 60 * 24 * 30  # seconds

    # -- database ------------------------------------------------------
    database_url: str = "postgresql+asyncpg://iterlab:iterlab@localhost:5432/iterlab"
    db_schema: str = "iterlab"
    db_auto_create: bool = True
    db_connect_retries: int = 10
    db_connect_retry_delay: float = 2.0
    db_echo: bool = False

    # -- redis -------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # -- artifact storage -----------------------------------------------
    storage_backend: Literal["filesystem"] = "filesystem"
    storage_path: str = "./data/artifacts"

    # -- http --------------------------------------------------------
    # NoDecode: take the raw env string (comma-separated) and let the validator
    # split it, instead of pydantic-settings trying to JSON-decode it.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    api_prefix: str = "/api/v1"

    # -- instance (deployment-specific, never committed) ----------------
    # Directory holding this deployment's private lab definitions and adapter
    # plugins. Everything under it is git-ignored. If unset, IterLab looks for
    # an "instance/" directory next to the repo root and uses it when present.
    instance_dir: str | None = None
    # Owner for labs provisioned from instance config. Auto-created on startup.
    instance_owner_email: str = "instance@iterlab.local"
    instance_sync_on_startup: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
