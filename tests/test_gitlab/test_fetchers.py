"""Tests for entity fetchers."""

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
from delivery_intelligence.gitlab.exceptions import GitLabNotFoundError
from delivery_intelligence.gitlab.fetchers import FetchResult, GitLabFetcher
from delivery_intelligence.gitlab.rate_limiter import RateLimiter
from delivery_intelligence.gitlab.retry import RetryConfig

BASE_URL = "https://gitlab.example.com/api/v4"
FIXTURES = Path(__file__).parent.parent / "fixtures" / "gitlab"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


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
def fetcher(auth: GitLabAuth, settings: GitLabSettings) -> GitLabFetcher:
    http = httpx.AsyncClient(base_url=BASE_URL, headers=auth.get_headers())
    client = GitLabClient(auth=auth, settings=settings, http_client=http)
    rate_limiter = RateLimiter()
    retry_config = RetryConfig(max_retries=1, jitter=False)
    return GitLabFetcher(client=client, rate_limiter=rate_limiter,
                         retry_config=retry_config, per_page=20)


async def test_fetch_project_returns_project(fetcher: GitLabFetcher) -> None:
    raw = load_fixture("project.json")
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1").mock(return_value=httpx.Response(200, json=raw))
        project = await fetcher.fetch_project(1)
        assert project.id == 1
        assert project.name == "my-project"


async def test_fetch_project_404_raises_not_found(fetcher: GitLabFetcher) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/999").mock(return_value=httpx.Response(404, json={}))
        with pytest.raises(GitLabNotFoundError):
            await fetcher.fetch_project(999)


async def test_fetch_issues_returns_fetch_result(fetcher: GitLabFetcher) -> None:
    raw = load_fixture("issue.json")
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/issues").mock(
            return_value=httpx.Response(200, json=[raw], headers={"x-total": "1"})
        )
        result = await fetcher.fetch_issues(1)
        assert isinstance(result, FetchResult)
        assert len(result.items) == 1
        assert result.failures == 0


async def test_fetch_issues_empty_response(fetcher: GitLabFetcher) -> None:
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/issues").mock(
            return_value=httpx.Response(200, json=[])
        )
        result = await fetcher.fetch_issues(1)
        assert result.items == []
        assert result.failures == 0
        assert result.total_raw == 0


async def test_fetch_issues_mapping_failure_counted(fetcher: GitLabFetcher) -> None:
    invalid_item = {"id": 999}  # missing required fields
    valid_item = load_fixture("issue.json")
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/issues").mock(
            return_value=httpx.Response(200, json=[valid_item, invalid_item])
        )
        result = await fetcher.fetch_issues(1)
        assert result.failures == 1
        assert len(result.items) == 1
        assert result.total_raw == 2


async def test_fetch_merge_requests(fetcher: GitLabFetcher) -> None:
    raw = load_fixture("merge_request.json")
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/merge_requests").mock(
            return_value=httpx.Response(200, json=[raw])
        )
        result = await fetcher.fetch_merge_requests(1)
        assert len(result.items) == 1
        assert result.failures == 0


async def test_fetch_pipelines(fetcher: GitLabFetcher) -> None:
    raw = load_fixture("pipeline.json")
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/pipelines").mock(
            return_value=httpx.Response(200, json=[raw])
        )
        result = await fetcher.fetch_pipelines(1)
        assert len(result.items) == 1


async def test_fetch_milestones(fetcher: GitLabFetcher) -> None:
    raw = load_fixture("milestone.json")
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/milestones").mock(
            return_value=httpx.Response(200, json=[raw])
        )
        result = await fetcher.fetch_milestones(1)
        assert len(result.items) == 1


async def test_fetch_contributors(fetcher: GitLabFetcher) -> None:
    raw = load_fixture("contributor.json")
    with respx.mock(base_url=BASE_URL) as mock:
        mock.get("/projects/1/members/all").mock(
            return_value=httpx.Response(200, json=[raw])
        )
        result = await fetcher.fetch_contributors(1)
        assert len(result.items) == 1


async def test_fetch_all_project_data_returns_dict(fetcher: GitLabFetcher) -> None:
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

    assert "issues" in results
    assert "merge_requests" in results
    assert "pipelines" in results
    assert "milestones" in results
    assert "contributors" in results
    assert len(results["issues"].items) == 1
