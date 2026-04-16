"""Rate-limit detection and adaptive throttling for GitLab API requests."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

from delivery_intelligence.core.logging import get_logger

_RATE_LIMIT_BUFFER_THRESHOLD: int = 5


@dataclass
class RateLimitState:
    """Current observed rate-limit state from GitLab response headers."""

    limit: int | None = None
    remaining: int | None = None
    reset_at: float | None = None
    retry_after: float | None = None


class RateLimiter:
    """Tracks GitLab rate-limit headers and pauses requests when limits are reached.

    Handles: 429 Retry-After, remaining=0, and pre-emptive throttling below buffer.
    """

    def __init__(self, buffer_threshold: int = _RATE_LIMIT_BUFFER_THRESHOLD) -> None:
        self._buffer_threshold = buffer_threshold
        self._state = RateLimitState()
        self._wait_count: int = 0
        self._logger = get_logger("gitlab.rate_limiter")

    def update(self, response: httpx.Response) -> None:
        """Parse rate-limit headers from the response and update internal state."""
        headers = response.headers
        self._state.limit = _parse_int_header(headers.get("RateLimit-Limit"))
        self._state.remaining = _parse_int_header(headers.get("RateLimit-Remaining"))
        self._state.reset_at = _parse_float_header(headers.get("RateLimit-Reset"))

        if response.status_code == 429:
            self._state.retry_after = _parse_float_header(headers.get("Retry-After"))
            self._logger.warning(
                "rate_limit_exceeded",
                status_code=429,
                retry_after=self._state.retry_after,
                reset_at=self._state.reset_at,
            )
        else:
            self._state.retry_after = None
            if self._state.remaining is not None:
                if self._state.remaining == 0:
                    self._logger.warning(
                        "rate_limit_remaining_zero",
                        remaining=self._state.remaining,
                        reset_at=self._state.reset_at,
                    )
                elif self._state.remaining <= self._buffer_threshold:
                    self._logger.warning(
                        "rate_limit_approaching_threshold",
                        remaining=self._state.remaining,
                        threshold=self._buffer_threshold,
                    )
                else:
                    self._logger.debug(
                        "rate_limit_state_updated",
                        limit=self._state.limit,
                        remaining=self._state.remaining,
                    )

    async def wait_if_needed(self) -> bool:
        """Sleep if rate-limited. Returns True if slept, False if no wait needed."""
        now = time.time()

        # 429 retry-after: sleep the requested duration
        if self._state.retry_after is not None:
            wait_secs = max(self._state.retry_after, 0.0)
            self._logger.info(
                "rate_limit_wait_started",
                reason="retry_after",
                wait_seconds=wait_secs,
            )
            await asyncio.sleep(wait_secs)
            self._wait_count += 1
            self._state.retry_after = None
            return True

        # remaining=0: sleep until reset_at
        if self._state.remaining is not None and self._state.remaining == 0:
            if self._state.reset_at is not None:
                wait_secs = max(self._state.reset_at - now, 0.0)
            else:
                wait_secs = 1.0
            self._logger.info(
                "rate_limit_wait_started",
                reason="remaining_zero",
                wait_seconds=wait_secs,
                reset_at=self._state.reset_at,
            )
            await asyncio.sleep(wait_secs)
            self._wait_count += 1
            return True

        # pre-emptive throttle below buffer threshold
        if (
            self._state.remaining is not None
            and self._state.remaining <= self._buffer_threshold
        ):
            wait_secs = 1.0
            self._logger.info(
                "rate_limit_wait_started",
                reason="pre_emptive_throttle",
                remaining=self._state.remaining,
                wait_seconds=wait_secs,
            )
            await asyncio.sleep(wait_secs)
            self._wait_count += 1
            return True

        return False

    def is_rate_limited(self) -> bool:
        """Return True if currently in a rate-limited state."""
        return (
            self._state.retry_after is not None
            or (self._state.remaining is not None and self._state.remaining == 0)
        )

    def get_state(self) -> RateLimitState:
        """Return the current rate-limit state."""
        return RateLimitState(
            limit=self._state.limit,
            remaining=self._state.remaining,
            reset_at=self._state.reset_at,
            retry_after=self._state.retry_after,
        )

    def get_wait_count(self) -> int:
        """Return the total number of waits performed."""
        return self._wait_count


def _parse_int_header(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_float_header(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
