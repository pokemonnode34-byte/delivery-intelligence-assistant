"""High-level entity fetchers combining client, pagination, retry, and mappers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from delivery_intelligence.core.logging import get_logger
from delivery_intelligence.gitlab.client import GitLabClient
from delivery_intelligence.gitlab.mappers import (
    map_contributor,
    map_issue,
    map_merge_request,
    map_milestone,
    map_pipeline,
    map_project,
)
from delivery_intelligence.gitlab.pagination import RequestFn, paginate_all
from delivery_intelligence.gitlab.rate_limiter import RateLimiter
from delivery_intelligence.gitlab.retry import RetryConfig, retry_request
from delivery_intelligence.models.base import BaseEntity
from delivery_intelligence.models.project import Project

_MAX_CONCURRENT_FETCHES: int = 5


@dataclass
class FetchResult:
    """Result of a paginated entity fetch with failure tracking."""

    items: list[BaseEntity]
    failures: int
    total_raw: int


class GitLabFetcher:
    """High-level fetcher that combines pagination, retry, rate-limiting, and mapping.

    All fetcher methods route requests through retry_request() per Architectural Invariant 1.
    Direct calls to client.get() or client.request() are prohibited in this class.
    """

    def __init__(
        self,
        client: GitLabClient,
        rate_limiter: RateLimiter,
        retry_config: RetryConfig,
        per_page: int = 100,
    ) -> None:
        self._client = client
        self._rate_limiter = rate_limiter
        self._retry_config = retry_config
        self._per_page = per_page
        self._logger = get_logger("gitlab.fetcher")

    def _make_request_fn(self, timeout: float | None = None) -> RequestFn:
        """Return a RequestFn that wraps retry_request() with this fetcher's config."""

        async def _request_fn(
            method: str, path: str, params: dict[str, Any] | None = None
        ) -> httpx.Response:
            return await retry_request(
                client=self._client,
                method=method,
                path=path,
                params=params,
                config=self._retry_config,
                rate_limiter=self._rate_limiter,
                timeout=timeout,
            )

        return _request_fn

    async def fetch_project(self, project_id: int) -> Project:
        """Fetch a single project by ID.

        Raises GitLabNotFoundError if the project does not exist.
        """
        response = await retry_request(
            client=self._client,
            method="GET",
            path=f"/projects/{project_id}",
            config=self._retry_config,
            rate_limiter=self._rate_limiter,
            timeout=self._client.default_timeout,
        )
        try:
            return map_project(response.json())
        except (ValueError, KeyError) as e:
            self._logger.error(
                "project_mapping_failed",
                project_id=project_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise ValueError(f"Failed to map project {project_id}: {e}") from e

    async def fetch_issues(
        self,
        project_id: int,
        state: str | None = None,
        updated_after: str | None = None,
    ) -> FetchResult:
        """Fetch all issues for a project with optional filters."""
        params: dict[str, Any] = {}
        if state is not None:
            params["state"] = state
        if updated_after is not None:
            params["updated_after"] = updated_after

        request_fn = self._make_request_fn(timeout=self._client.long_timeout)
        raw_items = await paginate_all(
            request_fn,
            f"/projects/{project_id}/issues",
            params,
            per_page=self._per_page,
        )
        return self._map_batch(raw_items, map_issue, "issue", project_id)

    async def fetch_merge_requests(
        self,
        project_id: int,
        state: str | None = None,
        updated_after: str | None = None,
    ) -> FetchResult:
        """Fetch all merge requests for a project with optional filters."""
        params: dict[str, Any] = {}
        if state is not None:
            params["state"] = state
        if updated_after is not None:
            params["updated_after"] = updated_after

        request_fn = self._make_request_fn(timeout=self._client.long_timeout)
        raw_items = await paginate_all(
            request_fn,
            f"/projects/{project_id}/merge_requests",
            params,
            per_page=self._per_page,
        )
        return self._map_batch(raw_items, map_merge_request, "merge_request", project_id)

    async def fetch_pipelines(
        self,
        project_id: int,
        ref: str | None = None,
        updated_after: str | None = None,
    ) -> FetchResult:
        """Fetch all pipelines for a project with optional filters."""
        params: dict[str, Any] = {}
        if ref is not None:
            params["ref"] = ref
        if updated_after is not None:
            params["updated_after"] = updated_after

        request_fn = self._make_request_fn(timeout=self._client.long_timeout)
        raw_items = await paginate_all(
            request_fn,
            f"/projects/{project_id}/pipelines",
            params,
            per_page=self._per_page,
        )
        return self._map_batch(raw_items, map_pipeline, "pipeline", project_id)

    async def fetch_milestones(
        self,
        project_id: int,
        state: str | None = None,
    ) -> FetchResult:
        """Fetch all milestones for a project."""
        params: dict[str, Any] = {}
        if state is not None:
            params["state"] = state

        request_fn = self._make_request_fn(timeout=self._client.long_timeout)
        raw_items = await paginate_all(
            request_fn,
            f"/projects/{project_id}/milestones",
            params,
            per_page=self._per_page,
        )
        return self._map_batch(raw_items, map_milestone, "milestone", project_id)

    async def fetch_contributors(self, project_id: int) -> FetchResult:
        """Fetch all members/contributors for a project."""
        request_fn = self._make_request_fn(timeout=self._client.long_timeout)
        raw_items = await paginate_all(
            request_fn,
            f"/projects/{project_id}/members/all",
            per_page=self._per_page,
        )
        return self._map_batch(raw_items, map_contributor, "contributor", project_id)

    async def fetch_all_project_data(
        self, project_id: int
    ) -> dict[str, FetchResult]:
        """Fetch all entity types concurrently with a semaphore-limited concurrency."""
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

        async def guarded(key: str, coro: Any) -> tuple[str, Any]:
            async with semaphore:
                return key, await coro

        tasks = [
            guarded("issues", self.fetch_issues(project_id)),
            guarded("merge_requests", self.fetch_merge_requests(project_id)),
            guarded("pipelines", self.fetch_pipelines(project_id)),
            guarded("milestones", self.fetch_milestones(project_id)),
            guarded("contributors", self.fetch_contributors(project_id)),
        ]

        results_raw = await asyncio.gather(*tasks, return_exceptions=True)
        results: dict[str, FetchResult] = {}

        for item in results_raw:
            if isinstance(item, Exception):
                self._logger.error(
                    "fetch_all_project_data_partial_failure",
                    project_id=project_id,
                    error_type=type(item).__name__,
                    error=str(item),
                )
                continue
            key, result = item
            results[key] = result

        return results

    def _map_batch(
        self,
        raw_items: list[dict[str, Any]],
        mapper: Any,
        entity_type: str,
        project_id: int,
    ) -> FetchResult:
        """Map a batch of raw items, tracking failures without crashing the batch."""
        mapped: list[BaseEntity] = []
        failures = 0
        for raw in raw_items:
            try:
                mapped.append(mapper(raw))
            except (ValueError, Exception) as e:
                failures += 1
                self._logger.error(
                    "entity_mapping_failed",
                    entity_type=entity_type,
                    entity_id=raw.get("id", "unknown"),
                    project_id=project_id,
                    error_type=type(e).__name__,
                    error=str(e),
                )
        return FetchResult(items=mapped, failures=failures, total_raw=len(raw_items))
