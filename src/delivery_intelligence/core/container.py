"""Dependency injection container for Delivery Intelligence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth
from delivery_intelligence.core.logging import get_logger, setup_logging

if TYPE_CHECKING:
    from delivery_intelligence.gitlab.client import GitLabClient
    from delivery_intelligence.gitlab.fetchers import GitLabFetcher
    from delivery_intelligence.gitlab.rate_limiter import RateLimiter
    from delivery_intelligence.gitlab.work_items import WorkItemDetector, WorkItemDetectionResult


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
        self._gitlab_client: GitLabClient | None = None
        self._rate_limiter: RateLimiter | None = None
        self._fetcher: GitLabFetcher | None = None
        self._work_item_detector: WorkItemDetector | None = None

    def initialize(self) -> None:
        """Initialize all dependencies.

        1. Sets up logging.
        2. Creates GitLabAuth from settings.
        3. Creates GitLab HTTP client, rate limiter, fetcher, and work item detector.
        4. Logs startup summary (no secrets).
        5. Marks the container as initialized.
        """
        from delivery_intelligence.gitlab.client import GitLabClient
        from delivery_intelligence.gitlab.fetchers import GitLabFetcher
        from delivery_intelligence.gitlab.rate_limiter import RateLimiter
        from delivery_intelligence.gitlab.retry import RetryConfig
        from delivery_intelligence.gitlab.work_items import WorkItemDetector

        setup_logging(self._settings.logging)
        self._auth = create_auth(self._settings.gitlab)
        self._logger = get_logger("container")

        self._rate_limiter = RateLimiter()
        self._gitlab_client = GitLabClient(
            auth=self._auth,
            settings=self._settings.gitlab,
        )
        retry_config = RetryConfig(
            max_retries=self._settings.gitlab.max_retries,
        )
        self._fetcher = GitLabFetcher(
            client=self._gitlab_client,
            rate_limiter=self._rate_limiter,
            retry_config=retry_config,
            per_page=self._settings.gitlab.per_page,
        )
        self._work_item_detector = WorkItemDetector(
            client=self._gitlab_client,
            rate_limiter=self._rate_limiter,
            retry_config=retry_config,
        )

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

    def get_gitlab_client(self) -> GitLabClient:
        """Return the GitLabClient instance. Requires initialization."""
        self._check_initialized()
        assert self._gitlab_client is not None
        return self._gitlab_client

    def get_rate_limiter(self) -> RateLimiter:
        """Return the RateLimiter instance. Requires initialization."""
        self._check_initialized()
        assert self._rate_limiter is not None
        return self._rate_limiter

    def get_fetcher(self) -> GitLabFetcher:
        """Return the GitLabFetcher instance. Requires initialization."""
        self._check_initialized()
        assert self._fetcher is not None
        return self._fetcher

    def get_work_item_detector(self) -> WorkItemDetector:
        """Return the WorkItemDetector instance. Requires initialization."""
        self._check_initialized()
        assert self._work_item_detector is not None
        return self._work_item_detector

    async def detect_work_items(self, project_id: int) -> WorkItemDetectionResult:
        """Detect work item support for a project. Delegates to WorkItemDetector."""
        return await self.get_work_item_detector().detect(project_id)

    def shutdown(self) -> None:
        """Shut down the container and clean up synchronous resources.

        Does not close the async HTTP client — call async_close() for that.
        """
        if self._logger is not None:
            self._logger.info("system_shutting_down", app_name=self._settings.app_name)
        if self._work_item_detector is not None:
            self._work_item_detector.clear_cache()
        self._initialized = False
        self._auth = None
        self._logger = None
        self._gitlab_client = None
        self._rate_limiter = None
        self._fetcher = None
        self._work_item_detector = None

    async def async_close(self) -> None:
        """Close async resources (HTTP client). Call before process exit."""
        if self._gitlab_client is not None:
            await self._gitlab_client.close()

    def _check_initialized(self) -> None:
        """Raise RuntimeError if the container has not been initialized."""
        if not self._initialized:
            raise RuntimeError("Container not initialized. Call initialize() first.")


def create_container(settings: AppSettings) -> Container:
    """Factory function that creates a Container. Does NOT call initialize()."""
    return Container(settings)
