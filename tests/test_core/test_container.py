"""Tests for the dependency injection container."""

from __future__ import annotations

import pytest

from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.auth import GitLabAuth
from delivery_intelligence.core.container import Container, create_container
from delivery_intelligence.gitlab.client import GitLabClient
from delivery_intelligence.gitlab.fetchers import GitLabFetcher
from delivery_intelligence.gitlab.rate_limiter import RateLimiter
from delivery_intelligence.gitlab.work_items import WorkItemDetector


def test_create_container_returns_container() -> None:
    settings = AppSettings()
    container = create_container(settings)
    assert isinstance(container, Container)


def test_get_settings_before_initialize() -> None:
    settings = AppSettings()
    container = create_container(settings)
    result = container.get_settings()
    assert result is settings


def test_initialize_completes_without_error() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()


def test_get_auth_returns_gitlab_auth() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    auth = container.get_auth()
    assert isinstance(auth, GitLabAuth)


def test_get_logger_returns_logger() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    logger = container.get_logger("test")
    assert logger is not None


def test_get_auth_before_initialize_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_auth()


def test_get_logger_before_initialize_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_logger("test")


def test_shutdown_sets_initialized_false() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    container.shutdown()
    assert container._initialized is False


def test_post_shutdown_get_auth_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    container.shutdown()
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_auth()


def test_conftest_test_container_fixture(test_container: Container) -> None:
    auth = test_container.get_auth()
    assert isinstance(auth, GitLabAuth)


def test_get_gitlab_client_returns_client() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    client = container.get_gitlab_client()
    assert isinstance(client, GitLabClient)


def test_get_rate_limiter_returns_rate_limiter() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    rl = container.get_rate_limiter()
    assert isinstance(rl, RateLimiter)


def test_get_fetcher_returns_fetcher() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    fetcher = container.get_fetcher()
    assert isinstance(fetcher, GitLabFetcher)


def test_get_work_item_detector_returns_detector() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    detector = container.get_work_item_detector()
    assert isinstance(detector, WorkItemDetector)


def test_get_gitlab_client_before_initialize_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_gitlab_client()


def test_get_fetcher_before_initialize_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_fetcher()


def test_get_work_item_detector_before_initialize_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_work_item_detector()


async def test_async_close_does_not_raise() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    # Should not raise even though client owns the http connection
    await container.async_close()
    container.shutdown()


async def test_detect_work_items_delegates_to_detector() -> None:
    import httpx
    import respx
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    base_url = str(settings.gitlab.url) + "/api/" + settings.gitlab.api_version
    with respx.mock(base_url=base_url) as mock:
        mock.get("/projects/1/work_items").mock(
            return_value=httpx.Response(200, json=[])
        )
        result = await container.detect_work_items(1)
        from delivery_intelligence.gitlab.work_items import WorkItemSupport
        assert result.support == WorkItemSupport.WORK_ITEMS_AVAILABLE
    container.shutdown()
