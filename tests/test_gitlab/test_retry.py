"""Tests for retry logic."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from pydantic import SecretStr

from delivery_intelligence.config.settings import GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth
from delivery_intelligence.gitlab.client import GitLabClient
from delivery_intelligence.gitlab.exceptions import (
    GitLabAuthError,
    GitLabNotFoundError,
    GitLabServerError,
)
from delivery_intelligence.gitlab.retry import RetryConfig, calculate_delay, retry_request

BASE_URL = "https://gitlab.example.com/api/v4"


@pytest.fixture
def settings() -> GitLabSettings:
    return GitLabSettings(
        url="https://gitlab.example.com",
        token=SecretStr("test-token"),
        timeout=10,
        max_retries=3,
        per_page=20,
    )


@pytest.fixture
def auth(settings: GitLabSettings) -> GitLabAuth:
    return create_auth(settings)


def _make_client(auth: GitLabAuth, settings: GitLabSettings) -> tuple[GitLabClient, httpx.AsyncClient]:
    http = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers())
    client = GitLabClient(auth=auth, settings=settings, http_client=http)
    return client, http


def test_calculate_delay_no_jitter() -> None:
    config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
    assert calculate_delay(1, config) == 1.0
    assert calculate_delay(2, config) == 2.0
    assert calculate_delay(3, config) == 4.0


def test_calculate_delay_capped_at_max() -> None:
    config = RetryConfig(base_delay=1.0, max_delay=5.0, exponential_base=2.0, jitter=False)
    assert calculate_delay(10, config) == 5.0


async def test_success_on_first_attempt(auth: GitLabAuth, settings: GitLabSettings) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1").mock(return_value=httpx.Response(200, json={"id": 1}))
        client, _ = _make_client(auth, settings)
        config = RetryConfig(max_retries=3, jitter=False)
        response = await retry_request(client, "GET", "/projects/1", config=config)
        assert response.status_code == 200
        assert client.metrics.retries == 0
        await client.close()


async def test_retry_on_500_then_success(
    auth: GitLabAuth, settings: GitLabSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("delivery_intelligence.gitlab.retry.asyncio.sleep", AsyncMock())
    responses = [httpx.Response(500, json={}), httpx.Response(200, json={"id": 1})]
    call_count = 0

    with respx.mock(base_url=BASE_URL) as mock:
        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            r = responses[call_count]
            call_count += 1
            return r
        mock.get("/projects/1").mock(side_effect=side_effect)
        client, _ = _make_client(auth, settings)
        config = RetryConfig(max_retries=3, jitter=False)
        response = await retry_request(client, "GET", "/projects/1", config=config)
        assert response.status_code == 200
        assert client.metrics.retries == 1
        await client.close()


async def test_exhausted_retries_raises_server_error(
    auth: GitLabAuth, settings: GitLabSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("delivery_intelligence.gitlab.retry.asyncio.sleep", AsyncMock())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/fail").mock(return_value=httpx.Response(500, json={}))
        client, _ = _make_client(auth, settings)
        config = RetryConfig(max_retries=2, jitter=False)
        with pytest.raises(GitLabServerError):
            await retry_request(client, "GET", "/fail", config=config)
        assert client.metrics.failures == 1
        await client.close()


async def test_no_retry_on_401(
    auth: GitLabAuth, settings: GitLabSettings
) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/auth-fail").mock(return_value=httpx.Response(401, json={}))
        client, _ = _make_client(auth, settings)
        config = RetryConfig(max_retries=3, jitter=False)
        with pytest.raises(GitLabAuthError):
            await retry_request(client, "GET", "/auth-fail", config=config)
        assert client.metrics.retries == 0
        assert client.metrics.failures == 1
        await client.close()


async def test_no_retry_on_404(
    auth: GitLabAuth, settings: GitLabSettings
) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/not-found").mock(return_value=httpx.Response(404, json={}))
        client, _ = _make_client(auth, settings)
        config = RetryConfig(max_retries=3, jitter=False)
        with pytest.raises(GitLabNotFoundError):
            await retry_request(client, "GET", "/not-found", config=config)
        assert client.metrics.retries == 0
        await client.close()


async def test_retry_on_connect_timeout(
    auth: GitLabAuth, settings: GitLabSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("delivery_intelligence.gitlab.retry.asyncio.sleep", AsyncMock())
    call_count = 0

    async def mock_request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.ConnectTimeout("timeout")
        return httpx.Response(200, json={"id": 1})

    client, _ = _make_client(auth, settings)
    client.request = mock_request  # type: ignore[method-assign]
    config = RetryConfig(max_retries=3, jitter=False)
    response = await retry_request(client, "GET", "/projects/1", config=config)
    assert response.status_code == 200
    assert client.metrics.retries == 1
    await client.close()


async def test_correlation_id_consistent_across_retries(
    auth: GitLabAuth, settings: GitLabSettings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("delivery_intelligence.gitlab.retry.asyncio.sleep", AsyncMock())
    correlation_ids: list[str] = []

    async def mock_request(method: str, path: str, *, params: Any = None,
                           timeout: Any = None, correlation_id: Any = None) -> httpx.Response:
        if correlation_id is not None:
            correlation_ids.append(correlation_id)
        if len(correlation_ids) < 2:
            return httpx.Response(500, json={})
        return httpx.Response(200, json={"id": 1})

    client, _ = _make_client(auth, settings)
    client.request = mock_request  # type: ignore[method-assign]
    config = RetryConfig(max_retries=3, jitter=False)
    cid = "fixed-correlation-id"
    await retry_request(client, "GET", "/p", config=config, correlation_id=cid)
    assert all(c == cid for c in correlation_ids)
    await client.close()
