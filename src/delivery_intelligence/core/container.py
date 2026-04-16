"""Dependency injection container for Delivery Intelligence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth
from delivery_intelligence.core.logging import get_logger, setup_logging

if TYPE_CHECKING:
    pass


class Container:
    """Application dependency container.

    Wires together configuration, logging, authentication, and future services.
    All dependencies are explicitly injected and accessible through typed accessors.
    """

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._initialized: bool = False
        self._auth: GitLabAuth | None = None
        self._logger: structlog.stdlib.BoundLogger | None = None

    def initialize(self) -> None:
        """Initialize all dependencies.

        1. Sets up logging.
        2. Creates GitLabAuth from settings.
        3. Logs startup summary (no secrets).
        4. Marks the container as initialized.
        """
        setup_logging(self._settings.logging)
        self._auth = create_auth(self._settings.gitlab)
        self._logger = get_logger("container")
        self._logger.info(
            "system_initialized",
            app_name=self._settings.app_name,
            version=self._settings.version,
            env=self._settings.env,
        )
        self._initialized = True

    def get_settings(self) -> AppSettings:
        """Return the application settings. Available before initialization."""
        return self._settings

    def get_logger(self, name: str) -> structlog.stdlib.BoundLogger:
        """Return a structlog bound logger. Requires initialization."""
        self._check_initialized()
        return get_logger(name)

    def get_auth(self) -> GitLabAuth:
        """Return the GitLabAuth instance. Requires initialization."""
        self._check_initialized()
        assert self._auth is not None
        return self._auth

    def shutdown(self) -> None:
        """Shut down the container and clean up resources."""
        if self._logger is not None:
            self._logger.info("system_shutting_down", app_name=self._settings.app_name)
        self._initialized = False
        self._auth = None
        self._logger = None

    def _check_initialized(self) -> None:
        """Raise RuntimeError if the container has not been initialized."""
        if not self._initialized:
            raise RuntimeError("Container not initialized. Call initialize() first.")


def create_container(settings: AppSettings) -> Container:
    """Factory function that creates a Container. Does NOT call initialize()."""
    return Container(settings)
