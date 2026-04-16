"""Tests for Work Item detection and fetching."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from pydantic import SecretStr

from delivery_intelligence.config.settings import GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth
from delivery_intelligence.gitlab.client import GitLabClient
from delivery_intelligence.gitlab.rate_limiter import RateLimiter
from delivery_intelligence.gitlab.retry import RetryConfig
from delivery_intelligence.gitlab.work_items import (
    WorkItemDetectionResult,
    WorkItemDetector,
    WorkItemSupport,
)

BASE_URL = "https://gitlab.example.com/api/v4"
FIXTURES = Path(__file__).parent.parent / "fixtures" / "gitlab"


@pytest.fixture
def settings() -> GitLabSettings:
    return GitLabSettings(
        url="https://gitlab.example.com",
        token=SecretStr("test-token"),
        timeout=10,
        max_retries=1,
        per_page=20,
    )


@pytest.fixture
def auth(settings: GitLabSettings) -> GitLabAuth:
    return create_auth(settings)


@pytest.fixture
def detector(auth: GitLabAuth, settings: GitLabSettings) -> WorkItemDetector:
    http = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers())
    client = GitLabClient(auth=auth, settings=settings, http_client=http)
    return WorkItemDetector(
        client=client,
        rate_limiter=RateLimiter(),
        retry_config=RetryConfig(max_retries=1, jitter=False),
    )


async def test_detect_work_items_available(detector: WorkItemDetector) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/work_items").mock(
            return_value=httpx.Response(200, json=[])
        )
        result = await detector.detect(1)
        assert result.support == WorkItemSupport.WORK_ITEMS_AVAILABLE


async def test_detect_issues_only_on_404(detector: WorkItemDetector) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/work_items").mock(
            return_value=httpx.Response(404, json={})
        )
        result = await detector.detect(1)
        assert result.support == WorkItemSupport.ISSUES_ONLY


async def test_detect_cache_hit(detector: WorkItemDetector) -> None:
    call_count = 0
    with respx.mock(base_url=BASE_URL) as mock:
        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=[])
        mock.get("/projects/1/work_items").mock(side_effect=handler)

        await detector.detect(1)
        await detector.detect(1)  # should hit cache
        assert call_count == 1


async def test_detect_non_fatal_on_error(detector: WorkItemDetector) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/work_items").mock(
            return_value=httpx.Response(500, json={})
        )
        result = await detector.detect(1)
        assert result.support == WorkItemSupport.UNKNOWN


def test_clear_cache(detector: WorkItemDetector) -> None:
    from datetime import datetime, timezone
    detector._cache[1] = WorkItemDetectionResult(
        support=WorkItemSupport.ISSUES_ONLY,
        work_item_types=[],
        message="cached",
        detected_at=datetime.now(timezone.utc),
    )
    assert detector.get_cached_result(1) is not None
    detector.clear_cache()
    assert detector.get_cached_result(1) is None


async def test_fetch_work_items_maps_to_issues(detector: WorkItemDetector) -> None:
    raw_items = json.loads((FIXTURES / "work_items_response.json").read_text())
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/work_items").mock(
            return_value=httpx.Response(200, json=raw_items)
        )
        issues = await detector.fetch_work_items(1, per_page=20)
        assert len(issues) == 1
        assert issues[0].title == "Work Item 1"
