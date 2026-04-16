"""Shared test fixtures for the delivery_intelligence test suite."""

from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from delivery_intelligence.config.settings import AppSettings, GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth
from delivery_intelligence.core.container import Container, create_container
from delivery_intelligence.gitlab.client import GitLabClient
from delivery_intelligence.gitlab.fetchers import GitLabFetcher
from delivery_intelligence.gitlab.rate_limiter import RateLimiter
from delivery_intelligence.gitlab.retry import RetryConfig

BASE_URL = "https://gitlab.example.com/api/v4"


@pytest.fixture
def test_settings() -> AppSettings:
    """Return AppSettings with development defaults for testing."""
    return AppSettings()


@pytest.fixture
def test_container(test_settings: AppSettings) -> Container:
    """Return an initialized Container with test settings."""
    container = create_container(test_settings)
    container.initialize()
    return container


@pytest.fixture
def test_gitlab_settings() -> GitLabSettings:
    return GitLabSettings(
        url="https://gitlab.example.com",
        token=SecretStr("test-token"),
        timeout=10,
        max_retries=1,
        per_page=20,
    )


@pytest.fixture
def test_gitlab_auth(test_gitlab_settings: GitLabSettings) -> GitLabAuth:
    return create_auth(test_gitlab_settings)


@pytest.fixture
def test_gitlab_client(test_gitlab_auth: GitLabAuth, test_gitlab_settings: GitLabSettings) -> GitLabClient:
    http = httpx.AsyncClient(base_url=BASE_URL, headers=test_gitlab_auth.get_headers())
    return GitLabClient(auth=test_gitlab_auth, settings=test_gitlab_settings, http_client=http)


@pytest.fixture
def test_fetcher(test_gitlab_client: GitLabClient) -> GitLabFetcher:
    return GitLabFetcher(
        client=test_gitlab_client,
        rate_limiter=RateLimiter(),
        retry_config=RetryConfig(max_retries=1, jitter=False),
        per_page=20,
    )
