"""GitLab integration package public API."""

from delivery_intelligence.gitlab.client import GitLabClient, RequestMetrics
from delivery_intelligence.gitlab.exceptions import (
    GitLabAPIError,
    GitLabAuthError,
    GitLabConnectionError,
    GitLabForbiddenError,
    GitLabNotFoundError,
    GitLabRateLimitError,
    GitLabServerError,
    raise_for_status,
)
from delivery_intelligence.gitlab.fetchers import FetchResult, GitLabFetcher
from delivery_intelligence.gitlab.pagination import (
    PaginatedResponse,
    paginate,
    paginate_all,
    parse_pagination_headers,
)
from delivery_intelligence.gitlab.rate_limiter import RateLimiter, RateLimitState
from delivery_intelligence.gitlab.retry import RetryConfig, retry_request
from delivery_intelligence.gitlab.work_items import (
    WorkItemDetectionResult,
    WorkItemDetector,
    WorkItemSupport,
)

__all__ = [
    "GitLabClient",
    "RequestMetrics",
    "GitLabAPIError",
    "GitLabAuthError",
    "GitLabConnectionError",
    "GitLabForbiddenError",
    "GitLabNotFoundError",
    "GitLabRateLimitError",
    "GitLabServerError",
    "raise_for_status",
    "FetchResult",
    "GitLabFetcher",
    "PaginatedResponse",
    "paginate",
    "paginate_all",
    "parse_pagination_headers",
    "RateLimiter",
    "RateLimitState",
    "RetryConfig",
    "retry_request",
    "WorkItemDetectionResult",
    "WorkItemDetector",
    "WorkItemSupport",
]
