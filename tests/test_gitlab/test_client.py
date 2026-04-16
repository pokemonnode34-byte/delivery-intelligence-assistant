"""Tests for the async GitLab HTTP client."""

from __future__ import annotations

import pytest
import httpx
import respx

from delivery_intelligence.config.settings import GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth
from delivery_intelligence.gitlab.client import GitLabClient
from pydantic import SecretStr


BASE_URL = "https://gitlab.example.com/api/v4"


@pytest.fixture
def settings() -> GitLabSettings:
    return GitLabSettings(
        url="https://gitlab.example.com",
        token=SecretStr("test-token"),
        timeout=10,
        max_retries=2,
        per_page=20,
    )


@pytest.fixture
def auth(settings: GitLabSettings) -> GitLabAuth:
    return create_auth(settings)


async def test_client_sends_get_request(settings: GitLabSettings, auth: GitLabAuth) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1").mock(return_value=httpx.Response(200, json={"id": 1}))
        http_client = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers())
        client = GitLabClient(auth=auth, settings=settings, http_client=http_client)
        response = await client.get("/projects/1")
        assert response.status_code == 200
        await client.close()


async def test_client_increments_total_requests(settings: GitLabSettings, auth: GitLabAuth) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects").mock(return_value=httpx.Response(200, json=[]))
        http_client = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers())
        client = GitLabClient(auth=auth, settings=settings, http_client=http_client)
        await client.get("/projects")
        await client.get("/projects")
        metrics = client.get_metrics()
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 2
        await client.close()


async def test_client_increments_failures_on_http_error(settings: GitLabSettings, auth: GitLabAuth) -> None:
    async def raise_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("failed")

    transport = httpx.MockTransport(handler=raise_error)
    http_client = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers(), transport=transport)
    client = GitLabClient(auth=auth, settings=settings, http_client=http_client)
    with pytest.raises(httpx.HTTPError):
        await client.get("/projects")
    assert client.metrics.failures == 1
    await client.close()


async def test_client_context_manager(settings: GitLabSettings, auth: GitLabAuth) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects").mock(return_value=httpx.Response(200, json=[]))
        http_client = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers())
        async with GitLabClient(auth=auth, settings=settings, http_client=http_client) as client:
            response = await client.get("/projects")
            assert response.status_code == 200


async def test_client_get_metrics_returns_copy(settings: GitLabSettings, auth: GitLabAuth) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects").mock(return_value=httpx.Response(200, json=[]))
        http_client = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers())
        client = GitLabClient(auth=auth, settings=settings, http_client=http_client)
        m1 = client.get_metrics()
        await client.get("/projects")
        m2 = client.get_metrics()
        assert m1.total_requests == 0
        assert m2.total_requests == 1
        await client.close()


def test_client_timeout_tiering(settings: GitLabSettings, auth: GitLabAuth) -> None:
    client = GitLabClient(auth=auth, settings=settings,
                          http_client=httpx.AsyncClient(base_url=BASE_URL))
    assert client.default_timeout == float(settings.timeout)
    assert client.long_timeout == float(settings.timeout * 2)
