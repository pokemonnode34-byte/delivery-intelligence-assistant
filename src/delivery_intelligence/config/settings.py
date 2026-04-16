"""Configuration settings models for Delivery Intelligence."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


class GitLabSettings(BaseModel):
    """GitLab API connection configuration."""

    url: str = "https://gitlab.example.com"
    token: SecretStr = SecretStr("not-set")
    api_version: str = "v4"
    timeout: int = 30
    max_retries: int = 3
    per_page: int = 100

    @field_validator("url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("per_page")
    @classmethod
    def validate_per_page(cls, v: int) -> int:
        if not 1 <= v <= 100:
            raise ValueError("per_page must be between 1 and 100 inclusive")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("timeout must be greater than 0")
        return v


class LoggingSettings(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["json", "console"] = "json"
    output: Literal["stdout", "file"] = "stdout"
    file_path: Optional[Path] = None

    @model_validator(mode="after")
    def validate_file_path(self) -> "LoggingSettings":
        if self.output == "file" and self.file_path is None:
            raise ValueError("file_path is required when output is 'file'")
        return self


class DatabaseSettings(BaseModel):
    """Database configuration placeholder (not used in Phase 0)."""

    url: str = "sqlite:///delivery_intelligence.db"
    echo: bool = False


class AppSettings(BaseSettings):
    """Top-level application settings with environment variable support."""

    env: Literal["development", "staging", "production"] = "development"
    app_name: str = "delivery-intelligence"
    version: str = "0.1.0"
    debug: bool = False
    gitlab: GitLabSettings = GitLabSettings()
    logging: LoggingSettings = LoggingSettings()
    database: DatabaseSettings = DatabaseSettings()

    model_config = {
        "env_prefix": "DI_",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
    }

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Env vars have higher priority than init kwargs (YAML values).
        # This follows the 12-factor app pattern: env > config file > defaults.
        return env_settings, dotenv_settings, file_secret_settings, init_settings
