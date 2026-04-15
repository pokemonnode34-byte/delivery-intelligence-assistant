"""Dependency injection container.

The :class:`Container` wires together configuration, logging, and
authentication.  It is the single source of truth for shared dependencies
and must be passed explicitly to every module that requires them.  No
global singletons are used.
"""

import structlog

from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth
from delivery_intelligence.core.logging import get_logger, setup_logging


class Container:
    """Dependency container for the Delivery Intelligence system.

    Call :meth:`initialize` before accessing any dependencies.
    :meth:`get_settings` is the only method that works before initialisation.
    """

    def __init__(self, settings: AppSettings) -> None:
        self._settings: AppSettings = settings
        self._auth: GitLabAuth | None = None
        self._initialized: bool = False

    def initialize(self) -> None:
        """Set up logging, authentication, and mark the container as ready."""
        setup_logging(self._settings.logging)
        self._auth = create_auth(self._settings.gitlab)
        logger = get_logger("container")
        logger.info(
            "container_initialized",
            app_name=self._settings.app_name,
            version=self._settings.version,
            env=self._settings.env,
        )
        self._initialized = True

    def get_settings(self) -> AppSettings:
        """Return the application settings.

        Available before :meth:`initialize` is called.
        """
        return self._settings

    def get_logger(self, name: str) -> structlog.stdlib.BoundLogger:
        """Return a structlog bound logger.

        Requires :meth:`initialize` to have been called so that logging is
        configured before the first log call.
        """
        self._check_initialized()
        return get_logger(name)

    def get_auth(self) -> GitLabAuth:
        """Return the :class:`~delivery_intelligence.core.auth.GitLabAuth` instance.

        Requires :meth:`initialize` to have been called.
        """
        self._check_initialized()
        assert self._auth is not None  # guaranteed when _initialized is True
        return self._auth

    def shutdown(self) -> None:
        """Log a shutdown message and mark the container as uninitialised."""
        logger = get_logger("container")
        logger.info("container_shutdown")
        self._initialized = False

    def _check_initialized(self) -> None:
        """Raise RuntimeError if the container has not been initialised."""
        if not self._initialized:
            raise RuntimeError(
                "Container not initialized. Call initialize() first."
            )


def create_container(settings: AppSettings) -> Container:
    """Create a :class:`Container` without initialising it.

    The caller is responsible for calling :meth:`Container.initialize`.
    """
    return Container(settings)
