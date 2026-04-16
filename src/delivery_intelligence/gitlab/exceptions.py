"""Custom exceptions and status mapping for GitLab API responses."""

from __future__ import annotations

import re

import httpx

_TOKEN_PATTERNS = (
    re.compile(r"(glpat-)[A-Za-z0-9_\-]+", re.IGNORECASE),
    re.compile(r"(?i)\b(authorization)\s*:\s*bearer\s+[^\s,;]+"),
    re.compile(r"(?i)\b(private[_-]?token|access[_-]?token|token|password)\s*=\s*([^&\s]+)"),
    re.compile(r"(?i)\b(private[_-]?token|access[_-]?token|token|password)\s*:\s*([^\s,;]+)"),
)

_SAFE_URL_PATTERN = re.compile(r"^([^?#]+)")


def _mask_sensitive_text(value: str | None) -> str | None:
    if value is None:
        return None

    sanitized = value
    for pattern in _TOKEN_PATTERNS:
        sanitized = pattern.sub(lambda m: f"{m.group(1)}***", sanitized)
    return sanitized


def _safe_request_url(url: httpx.URL | str | None) -> str | None:
    if url is None:
        return None

    url_str = str(url)
    match = _SAFE_URL_PATTERN.match(url_str)
    if not match:
        return None
    return match.group(1)


def _parse_optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class GitLabAPIError(Exception):
    """Base exception for all GitLab API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
        request_url: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.message = _mask_sensitive_text(message) or ""
        self.status_code = status_code
        self.response_body = _mask_sensitive_text(response_body)
        self.request_url = _safe_request_url(request_url)
        self.correlation_id = _mask_sensitive_text(correlation_id)
        super().__init__(self.message)

    def __str__(self) -> str:
        status = self.status_code if self.status_code is not None else "unknown"
        text = f"GitLabAPIError({status}): {self.message}"
        if self.correlation_id is not None:
            return f"{text} [correlation_id={self.correlation_id}]"
        return text


class GitLabAuthError(GitLabAPIError):
    """Raised on HTTP 401 Unauthorized responses."""

    def __init__(
        self,
        message: str = "Authentication failed. Verify your GitLab token.",
        status_code: int | None = None,
        response_body: str | None = None,
        request_url: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body, request_url, correlation_id)


class GitLabForbiddenError(GitLabAPIError):
    """Raised on HTTP 403 Forbidden responses."""

    def __init__(
        self,
        message: str = "Access forbidden. Check project permissions.",
        status_code: int | None = None,
        response_body: str | None = None,
        request_url: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(message, status_code, response_body, request_url, correlation_id)


class GitLabNotFoundError(GitLabAPIError):
    """Raised on HTTP 404 Not Found responses."""

    def __init__(
        self,
        message: str = "Resource not found.",
        status_code: int | None = None,
        response_body: str | None = None,
        request_url: str | None = None,
        correlation_id: str | None = None,
        resource_type: str | None = None,
        resource_id: int | str | None = None,
    ) -> None:
        if resource_type is not None and resource_id is not None:
            message = f"{resource_type} {resource_id} not found."
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message, status_code, response_body, request_url, correlation_id)


class GitLabRateLimitError(GitLabAPIError):
    """Raised on HTTP 429 Too Many Requests responses."""

    def __init__(
        self,
        message: str = "GitLab API rate limit exceeded.",
        status_code: int | None = None,
        response_body: str | None = None,
        request_url: str | None = None,
        correlation_id: str | None = None,
        retry_after: float | None = None,
        reset_at: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        self.reset_at = reset_at
        super().__init__(message, status_code, response_body, request_url, correlation_id)


class GitLabServerError(GitLabAPIError):
    """Raised on HTTP 5xx responses."""


class GitLabConnectionError(GitLabAPIError):
    """Raised when retries are exhausted due to connection-level errors."""

    def __init__(
        self,
        cause: Exception,
        message: str = "Connection to GitLab API failed.",
        status_code: int | None = None,
        response_body: str | None = None,
        request_url: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.cause = cause
        super().__init__(message, status_code, response_body, request_url, correlation_id)


def raise_for_status(response: httpx.Response, correlation_id: str | None = None) -> None:
    """Raise a typed GitLab exception based on HTTP status code."""

    status_code = response.status_code
    if 200 <= status_code < 300:
        return

    request_url = _safe_request_url(response.request.url if response.request is not None else None)
    response_body = _mask_sensitive_text(response.text)
    if response_body is not None:
        response_body = response_body[:500]

    if status_code == 401:
        raise GitLabAuthError(
            status_code=status_code,
            response_body=response_body,
            request_url=request_url,
            correlation_id=correlation_id,
        )
    if status_code == 403:
        raise GitLabForbiddenError(
            status_code=status_code,
            response_body=response_body,
            request_url=request_url,
            correlation_id=correlation_id,
        )
    if status_code == 404:
        raise GitLabNotFoundError(
            status_code=status_code,
            response_body=response_body,
            request_url=request_url,
            correlation_id=correlation_id,
        )
    if status_code == 429:
        retry_after = _parse_optional_float(response.headers.get("Retry-After"))
        reset_at = _parse_optional_float(
            response.headers.get("RateLimit-Reset") or response.headers.get("X-RateLimit-Reset")
        )
        raise GitLabRateLimitError(
            status_code=status_code,
            response_body=response_body,
            request_url=request_url,
            correlation_id=correlation_id,
            retry_after=retry_after,
            reset_at=reset_at,
        )
    if 500 <= status_code < 600:
        raise GitLabServerError(
            message="GitLab server error.",
            status_code=status_code,
            response_body=response_body,
            request_url=request_url,
            correlation_id=correlation_id,
        )
    if 400 <= status_code < 500:
        raise GitLabAPIError(
            message="GitLab API request failed.",
            status_code=status_code,
            response_body=response_body,
            request_url=request_url,
            correlation_id=correlation_id,
        )
    raise GitLabAPIError(
        message="Unexpected GitLab API response status.",
        status_code=status_code,
        response_body=response_body,
        request_url=request_url,
        correlation_id=correlation_id,
    )
