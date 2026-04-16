"""Integration tests for GitLab client stack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr

from delivery_intelligence.config.settings import GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth
from delivery_intelligence.gitlab.client import GitLabClient
from delivery_intelligence.gitlab.fetchers import FetchResult, GitLabFetcher
from delivery_intelligence.gitlab.rate_limiter import RateLimiter
from delivery_intelligence.gitlab.retry import RetryConfig, retry_request
from delivery_intelligence.gitlab.work_items import WorkItemDetector, WorkItemSupport
from delivery_intelligence.gitlab.webhooks import (
    WebhookEvent,
    map_webhook_to_model,
    parse_webhook_event,
    validate_webhook_token,
)
from delivery_intelligence.models.issue import Issue
from delivery_intelligence.models.merge_request import MergeRequest
from delivery_intelligence.models.pipeline import Pipeline

BASE_URL = "https://gitlab.example.com/api/v4"
FIXTURES = Path(__file__).parent.parent / "fixtures" / "gitlab"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


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


@pytest.fixture
def client(auth: GitLabAuth, settings: GitLabSettings) -> GitLabClient:
    http = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers())
    return GitLabClient(auth=auth, settings=settings, http_client=http)


@pytest.fixture
def rate_limiter() -> RateLimiter:
    return RateLimiter()


@pytest.fixture
def retry_config() -> RetryConfig:
    return RetryConfig(max_retries=2, jitter=False)


@pytest.fixture
def fetcher(client: GitLabClient, rate_limiter: RateLimiter, retry_config: RetryConfig) -> GitLabFetcher:
    return GitLabFetcher(
        client=client,
        rate_limiter=rate_limiter,
        retry_config=retry_config,
        per_page=20,
    )


@pytest.fixture
def detector(client: GitLabClient, rate_limiter: RateLimiter, retry_config: RetryConfig) -> WorkItemDetector:
    return WorkItemDetector(
        client=client,
        rate_limiter=rate_limiter,
        retry_config=retry_config,
    )


# --- Client + Retry Integration ---

async def test_client_retry_on_500_then_success(
    client: GitLabClient, retry_config: RetryConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import AsyncMock
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

        response = await retry_request(client, "GET", "/projects/1", config=retry_config)
        assert response.status_code == 200
        assert client.metrics.retries == 1


# --- Fetcher + Pagination Integration ---

async def test_fetcher_paginates_issues(
    fetcher: GitLabFetcher, monkeypatch: pytest.MonkeyPatch
) -> None:
    issue_raw = load_fixture("issue.json")
    page1 = httpx.Response(
        200,
        json=[issue_raw],
        headers={"x-page": "1", "x-per-page": "1", "x-next-page": "2", "x-total": "2"},
    )
    page2_issue = {**issue_raw, "id": 101, "iid": 2}
    page2 = httpx.Response(
        200,
        json=[page2_issue],
        headers={"x-page": "2", "x-per-page": "1", "x-total": "2"},
    )
    responses = [page1, page2]
    call_count = 0

    with respx.mock(base_url=BASE_URL) as mock:
        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            r = responses[call_count]
            call_count += 1
            return r
        mock.get("/projects/1/issues").mock(side_effect=side_effect)

        result = await fetcher.fetch_issues(1)
        assert len(result.items) == 2
        assert call_count == 2


# --- Rate Limiter Integration ---

async def test_rate_limiter_wait_triggers_on_429(
    client: GitLabClient, rate_limiter: RateLimiter, retry_config: RetryConfig,
    monkeypatch: pytest.MonkeyPatch
) -> None:
    slept: list[float] = []

    async def mock_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("delivery_intelligence.gitlab.retry.asyncio.sleep", mock_sleep)
    monkeypatch.setattr("delivery_intelligence.gitlab.rate_limiter.asyncio.sleep", mock_sleep)

    responses = [
        httpx.Response(429, json={}, headers={"Retry-After": "1", "RateLimit-Remaining": "0"}),
        httpx.Response(200, json={"id": 1}),
    ]
    call_count = 0

    with respx.mock(base_url=BASE_URL) as mock:
        def side_effect(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            r = responses[call_count]
            call_count += 1
            return r
        mock.get("/projects/1").mock(side_effect=side_effect)

        response = await retry_request(
            client, "GET", "/projects/1",
            config=retry_config,
            rate_limiter=rate_limiter,
        )
        assert response.status_code == 200
        assert client.metrics.rate_limit_waits >= 1


# --- Work Item Detection Integration ---

async def test_work_item_detector_caches_result(detector: WorkItemDetector) -> None:
    call_count = 0
    with respx.mock(base_url=BASE_URL) as mock:
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=[])
        mock.get("/projects/1/work_items").mock(side_effect=handler)

        r1 = await detector.detect(1)
        r2 = await detector.detect(1)
        assert call_count == 1
        assert r1.support == r2.support == WorkItemSupport.WORK_ITEMS_AVAILABLE


async def test_work_item_detector_404_yields_issues_only(detector: WorkItemDetector) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/work_items").mock(return_value=httpx.Response(404, json={}))
        result = await detector.detect(1)
        assert result.support == WorkItemSupport.ISSUES_ONLY


# --- Webhook + Mapper Integration ---

def test_webhook_full_pipeline_issue() -> None:
    body = load_fixture("webhook_issue.json")
    headers = {"X-Gitlab-Event": "Issue Hook", "X-Gitlab-Token": "my-secret"}
    assert validate_webhook_token(headers, "my-secret") is True
    payload = parse_webhook_event(headers, body)
    assert payload.event_type == WebhookEvent.ISSUE
    model = map_webhook_to_model(payload)
    assert isinstance(model, Issue)
    assert model.title == "Fix the bug"


def test_webhook_full_pipeline_merge_request() -> None:
    body = load_fixture("webhook_merge_request.json")
    headers = {"X-Gitlab-Event": "Merge Request Hook"}
    payload = parse_webhook_event(headers, body)
    model = map_webhook_to_model(payload)
    assert isinstance(model, MergeRequest)


def test_webhook_full_pipeline_pipeline() -> None:
    body = load_fixture("webhook_pipeline.json")
    headers = {"X-Gitlab-Event": "Pipeline Hook"}
    payload = parse_webhook_event(headers, body)
    model = map_webhook_to_model(payload)
    assert isinstance(model, Pipeline)


# --- Metrics Integration ---

async def test_metrics_accumulate_across_requests(
    client: GitLabClient, retry_config: RetryConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    from unittest.mock import AsyncMock
    monkeypatch.setattr("delivery_intelligence.gitlab.retry.asyncio.sleep", AsyncMock())

    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1").mock(return_value=httpx.Response(200, json={"id": 1}))
        mock.get("/projects/2").mock(return_value=httpx.Response(404, json={}))

        await retry_request(client, "GET", "/projects/1", config=retry_config)
        from delivery_intelligence.gitlab.exceptions import GitLabNotFoundError
        with pytest.raises(GitLabNotFoundError):
            await retry_request(client, "GET", "/projects/2", config=retry_config)

        metrics = client.get_metrics()
        assert metrics.total_requests == 2
        assert metrics.successful_requests == 1
        assert metrics.failures == 1


# --- Full Stack: fetch_all_project_data ---

async def test_fetch_all_project_data_integration(fetcher: GitLabFetcher) -> None:
    issue_raw = load_fixture("issue.json")
    mr_raw = load_fixture("merge_request.json")
    pipeline_raw = load_fixture("pipeline.json")
    milestone_raw = load_fixture("milestone.json")
    contributor_raw = load_fixture("contributor.json")

    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/issues").mock(return_value=httpx.Response(200, json=[issue_raw]))
        mock.get("/projects/1/merge_requests").mock(return_value=httpx.Response(200, json=[mr_raw]))
        mock.get("/projects/1/pipelines").mock(return_value=httpx.Response(200, json=[pipeline_raw]))
        mock.get("/projects/1/milestones").mock(return_value=httpx.Response(200, json=[milestone_raw]))
        mock.get("/projects/1/members/all").mock(return_value=httpx.Response(200, json=[contributor_raw]))

        results = await fetcher.fetch_all_project_data(1)

    assert set(results.keys()) == {"issues", "merge_requests", "pipelines", "milestones", "contributors"}
    for key, result in results.items():
        assert isinstance(result, FetchResult)
        assert result.failures == 0
        assert len(result.items) == 1
