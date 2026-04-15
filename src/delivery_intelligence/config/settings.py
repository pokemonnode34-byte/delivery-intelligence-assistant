"""Application configuration models using Pydantic Settings."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class GitLabSettings(BaseModel):
    """Settings for the GitLab API connection."""

    url: str = "https://gitlab.example.com"
    token: SecretStr = SecretStr("not-set")
    api_version: str = "v4"
    timeout: int = 30
    max_retries: int = 3
    per_page: int = 100

    @field_validator("url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        """Remove trailing slashes from the base URL."""
        return v.rstrip("/")

    @field_validator("per_page")
    @classmethod
    def validate_per_page(cls, v: int) -> int:
        """Enforce per_page is between 1 and 100 inclusive."""
        if not 1 <= v <= 100:
            raise ValueError("per_page must be between 1 and 100 inclusive")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Enforce timeout is greater than zero."""
        if v <= 0:
            raise ValueError("timeout must be > 0")
        return v


class LoggingSettings(BaseModel):
    """Settings for the logging subsystem."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["json", "console"] = "json"
    output: Literal["stdout", "file"] = "stdout"
    file_path: Path | None = None

    @model_validator(mode="after")
    def validate_file_path(self) -> "LoggingSettings":
        """Require file_path when output is 'file'."""
        if self.output == "file" and self.file_path is None:
            raise ValueError("file_path is required when output='file'")
        return self


class DatabaseSettings(BaseModel):
    """Placeholder database settings (not active in Phase 0)."""

    url: str = "sqlite:///delivery_intelligence.db"
    echo: bool = False


class AppSettings(BaseSettings):
    """Top-level application settings.

    Loaded from YAML files and overridden by environment variables
    with the ``DI_`` prefix.
    """

    env: Literal["development", "staging", "production"] = "development"
    app_name: str = "delivery-intelligence"
    version: str = "0.1.0"
    debug: bool = False
    gitlab: GitLabSettings = GitLabSettings(
        url="https://gitlab.example.com",
        token=SecretStr("not-set"),
    )
    logging: LoggingSettings = LoggingSettings()
    database: DatabaseSettings = DatabaseSettings()

    model_config = SettingsConfigDict(
        env_prefix="DI_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Put env vars above constructor kwargs so env vars override YAML."""
        return env_settings, dotenv_settings, init_settings, file_secret_settings
