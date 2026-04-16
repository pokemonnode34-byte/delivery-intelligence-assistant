"""Retry logic with exponential backoff and jitter for GitLab API requests."""

from __future__ import annotations

import asyncio
import random
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from delivery_intelligence.gitlab.client import GitLabClient
from delivery_intelligence.gitlab.exceptions import (
    GitLabConnectionError,
    raise_for_status,
)
from delivery_intelligence.gitlab.rate_limiter import RateLimiter
from delivery_intelligence.core.logging import get_logger

_logger = get_logger("gitlab.retry")

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
_NON_RETRYABLE_STATUS_CODES = frozenset({400, 401, 403, 404})


@dataclass
class RetryConfig:
    """Configuration for retry behaviour with exponential backoff."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate exponential backoff delay with optional jitter.

    attempt is 1-indexed (first retry is attempt=1).
    Delay is capped at config.max_delay.
    Jitter applies a 0.5–1.5 multiplier when enabled.
    """
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    delay = min(delay, config.max_delay)
    if config.jitter:
        delay *= random.uniform(0.5, 1.5)
    return delay


def is_retryable_status(status_code: int) -> bool:
    """Return True if the status code warrants a retry."""
    return status_code in _RETRYABLE_STATUS_CODES


def is_retryable_exception(exc: Exception) -> bool:
    """Return True if the exception type warrants a retry."""
    return isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError))


async def retry_request(
    client: GitLabClient,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    config: RetryConfig | None = None,
    rate_limiter: RateLimiter | None = None,
    timeout: float | None = None,
    correlation_id: str | None = None,
) -> httpx.Response:
    """Execute an API request with retry, backoff, and optional rate-limit integration.

    Request flow per attempt:
      1. rate_limiter.wait_if_needed() (increments client.metrics.rate_limit_waits if waited)
      2. client.request(...)
      3. rate_limiter.update(response)

    On retryable response: log WARNING, sleep backoff, retry.
    On retryable exception: log WARNING, sleep backoff, retry.
    On exhausted retries (HTTP error): raise typed exception, increment failures.
    On exhausted retries (connection error): raise GitLabConnectionError, increment failures.
    On non-retryable 4xx: raise immediately via raise_for_status, increment failures.
    On success: return response.
    """
    if config is None:
        config = RetryConfig(max_retries=client._settings.max_retries)
    if correlation_id is None:
        correlation_id = uuid.uuid4().hex[:12]

    last_response: httpx.Response | None = None
    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        # Rate-limit wait before each attempt
        if rate_limiter is not None:
            waited = await rate_limiter.wait_if_needed()
            if waited:
                client.metrics.rate_limit_waits += 1

        try:
            response = await client.request(
                method=method,
                path=path,
                params=params,
                timeout=timeout,
                correlation_id=correlation_id,
            )
        except Exception as exc:
            last_exception = exc
            if is_retryable_exception(exc) and attempt < config.max_retries:
                delay = calculate_delay(attempt + 1, config)
                client.metrics.retries += 1
                _logger.warning(
                    "request_retrying_after_exception",
                    method=method,
                    path=path,
                    attempt=attempt + 1,
                    max_retries=config.max_retries,
                    delay=round(delay, 2),
                    error_type=type(exc).__name__,
                    correlation_id=correlation_id,
                )
                await asyncio.sleep(delay)
                continue
            # Exhausted or non-retryable exception
            client.metrics.failures += 1
            raise GitLabConnectionError(
                cause=exc,
                message="Connection to GitLab API failed.",
                correlation_id=correlation_id,
            ) from exc

        # Update rate limiter with response
        if rate_limiter is not None:
            rate_limiter.update(response)

        # Non-retryable 4xx: raise immediately
        if response.status_code in _NON_RETRYABLE_STATUS_CODES:
            client.metrics.failures += 1
            raise_for_status(response, correlation_id=correlation_id)
            # raise_for_status always raises for non-2xx, but satisfy type checker:
            return response  # pragma: no cover

        # Retryable response
        if is_retryable_status(response.status_code) and attempt < config.max_retries:
            last_response = response
            delay = calculate_delay(attempt + 1, config)
            client.metrics.retries += 1
            _logger.warning(
                "request_retrying_after_status",
                method=method,
                path=path,
                status_code=response.status_code,
                attempt=attempt + 1,
                max_retries=config.max_retries,
                delay=round(delay, 2),
                correlation_id=correlation_id,
            )
            await asyncio.sleep(delay)
            continue

        # Non-retryable non-2xx (unexpected 4xx, etc.)
        if not (200 <= response.status_code < 300):
            client.metrics.failures += 1
            raise_for_status(response, correlation_id=correlation_id)
            return response  # pragma: no cover

        # Success
        return response

    # Retries exhausted
    client.metrics.failures += 1
    if last_response is not None:
        raise_for_status(last_response, correlation_id=correlation_id)
    if last_exception is not None:
        raise GitLabConnectionError(
            cause=last_exception,
            message="Connection to GitLab API failed after all retries.",
            correlation_id=correlation_id,
        ) from last_exception

    raise RuntimeError(f"retry_request exhausted without response or exception — path={path}")
