"""Work Item detection and fetching for GitLab projects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from delivery_intelligence.core.logging import get_logger
from delivery_intelligence.gitlab.client import GitLabClient
from delivery_intelligence.gitlab.mappers import map_issue
from delivery_intelligence.gitlab.pagination import paginate_all
from delivery_intelligence.gitlab.rate_limiter import RateLimiter
from delivery_intelligence.gitlab.retry import RetryConfig, retry_request
from delivery_intelligence.models.issue import Issue


class WorkItemSupport(StrEnum):
    """Whether the GitLab project supports Work Items."""

    ISSUES_ONLY = "ISSUES_ONLY"
    WORK_ITEMS_AVAILABLE = "WORK_ITEMS_AVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass
class WorkItemDetectionResult:
    """Result of probing a project for Work Item support."""

    support: WorkItemSupport
    work_item_types: list[str]
    message: str
    detected_at: datetime


class WorkItemDetector:
    """Detects and caches whether a GitLab project supports Work Items.

    Cache is in-memory for the container lifetime.
    """

    def __init__(
        self,
        client: GitLabClient,
        rate_limiter: RateLimiter,
        retry_config: RetryConfig,
    ) -> None:
        self._client = client
        self._rate_limiter = rate_limiter
        self._retry_config = retry_config
        self._cache: dict[int, WorkItemDetectionResult] = {}
        self._logger = get_logger("gitlab.work_items")

    async def detect(self, project_id: int) -> WorkItemDetectionResult:
        """Probe a project for Work Item support. Returns cached result if available.

        200 → WORK_ITEMS_AVAILABLE
        404/400 → ISSUES_ONLY
        Other errors → UNKNOWN (non-fatal)
        """
        if project_id in self._cache:
            cached = self._cache[project_id]
            self._logger.debug(
                "work_item_detection_cache_hit",
                project_id=project_id,
                support=cached.support.value,
            )
            return cached

        probe_config = RetryConfig(
            max_retries=1,
            base_delay=self._retry_config.base_delay,
            max_delay=self._retry_config.max_delay,
            jitter=False,
        )

        try:
            response = await retry_request(
                client=self._client,
                method="GET",
                path=f"/projects/{project_id}/work_items",
                params={"per_page": 1},
                config=probe_config,
                rate_limiter=self._rate_limiter,
                timeout=self._client.default_timeout,
            )
            if response.status_code == 200:
                support = WorkItemSupport.WORK_ITEMS_AVAILABLE
                message = "Work Items API responded with 200"
            else:
                support = WorkItemSupport.ISSUES_ONLY
                message = f"Work Items API responded with {response.status_code}"
        except Exception as e:
            # 404/400 from raise_for_status become typed exceptions — treat as ISSUES_ONLY
            status_code = getattr(e, "status_code", None)
            if status_code in (404, 400):
                support = WorkItemSupport.ISSUES_ONLY
                message = f"Work Items API not available ({status_code})"
            else:
                support = WorkItemSupport.UNKNOWN
                message = f"Work Item detection failed: {type(e).__name__}"
                self._logger.warning(
                    "work_item_detection_failed",
                    project_id=project_id,
                    error_type=type(e).__name__,
                    error=str(e),
                )

        result = WorkItemDetectionResult(
            support=support,
            work_item_types=[],
            message=message,
            detected_at=datetime.now(timezone.utc),
        )
        self._cache[project_id] = result
        self._logger.info(
            "work_item_detection_result",
            project_id=project_id,
            support=support.value,
            message=message,
        )
        return result

    def get_cached_result(self, project_id: int) -> WorkItemDetectionResult | None:
        """Return cached detection result for a project, or None if not cached."""
        return self._cache.get(project_id)

    def clear_cache(self) -> None:
        """Clear all cached detection results."""
        self._cache.clear()
        self._logger.debug("work_item_detection_cache_cleared")

    async def fetch_work_items(self, project_id: int, per_page: int = 100) -> list[Issue]:
        """Fetch work items for a project, mapped to Issue domain models."""

        async def request_fn(method: str, path: str, params: Any = None) -> Any:
            return await retry_request(
                client=self._client,
                method=method,
                path=path,
                params=params,
                config=self._retry_config,
                rate_limiter=self._rate_limiter,
                timeout=self._client.long_timeout,
            )

        raw_items = await paginate_all(
            request_fn,
            f"/projects/{project_id}/work_items",
            per_page=per_page,
        )
        issues: list[Issue] = []
        for raw in raw_items:
            try:
                issues.append(map_issue(raw))
            except (ValueError, Exception) as e:
                self._logger.error(
                    "work_item_mapping_failed",
                    project_id=project_id,
                    entity_id=raw.get("id", "unknown"),
                    error_type=type(e).__name__,
                    error=str(e),
                )
        return issues
