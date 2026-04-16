"""Async GitLab HTTP client with auth, timeouts, correlation IDs, and request metrics."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from delivery_intelligence.config.settings import GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth
from delivery_intelligence.core.logging import get_logger


@dataclass
class RequestMetrics:
    """Tracks aggregate request outcomes for the client lifetime."""

    total_requests: int = 0
    successful_requests: int = 0
    retries: int = 0
    rate_limit_waits: int = 0
    failures: int = 0


class GitLabClient:
    """Async HTTP client for GitLab API requests.

    Wraps httpx.AsyncClient with authentication headers, tiered timeouts,
    correlation-ID-tagged structured logging, and request outcome metrics.
    """

    def __init__(
        self,
        auth: GitLabAuth,
        settings: GitLabSettings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._auth = auth
        self._settings = settings
        self.default_timeout = float(settings.timeout)
        self.long_timeout = float(settings.timeout * 2)
        self._logger = get_logger("gitlab.client")
        self.metrics = RequestMetrics()

        if http_client is not None:
            self._http_client = http_client
            self._owns_client = False
        else:
            self._http_client = httpx.AsyncClient(
                base_url=auth.get_base_url(),
                headers=auth.get_headers(),
                timeout=httpx.Timeout(settings.timeout),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
            self._owns_client = True

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        correlation_id: str | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request and return the raw response.

        Does NOT call raise_for_status — the retry layer handles that.
        Logs at DEBUG on entry and exit. Logs at ERROR on httpx.HTTPError.
        """
        if correlation_id is None:
            correlation_id = uuid.uuid4().hex[:12]

        self._logger.debug(
            "request_started",
            method=method,
            path=path,
            correlation_id=correlation_id,
        )

        self.metrics.total_requests += 1
        start_ms = time.monotonic() * 1000

        try:
            request_kwargs: dict[str, Any] = {}
            if params is not None:
                request_kwargs["params"] = params
            if timeout is not None:
                request_kwargs["timeout"] = timeout

            response = await self._http_client.request(method, path, **request_kwargs)
        except httpx.HTTPError as e:
            self.metrics.failures += 1
            self._logger.error(
                "request_http_error",
                method=method,
                path=path,
                correlation_id=correlation_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

        elapsed_ms = time.monotonic() * 1000 - start_ms

        self._logger.debug(
            "request_completed",
            method=method,
            path=path,
            status_code=response.status_code,
            elapsed_ms=round(elapsed_ms, 1),
            correlation_id=correlation_id,
        )

        if 200 <= response.status_code < 300:
            self.metrics.successful_requests += 1

        return response

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        correlation_id: str | None = None,
    ) -> httpx.Response:
        """Convenience GET method wrapping request()."""
        return await self.request("GET", path, params, timeout, correlation_id)

    def get_metrics(self) -> RequestMetrics:
        """Return a copy of the current request metrics."""
        return RequestMetrics(
            total_requests=self.metrics.total_requests,
            successful_requests=self.metrics.successful_requests,
            retries=self.metrics.retries,
            rate_limit_waits=self.metrics.rate_limit_waits,
            failures=self.metrics.failures,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client if owned by this instance."""
        if self._owns_client:
            await self._http_client.aclose()
            self._logger.info("gitlab_client_closed")

    async def __aenter__(self) -> "GitLabClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
