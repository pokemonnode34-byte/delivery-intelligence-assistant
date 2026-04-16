"""Tests for rate-limit handler."""

from __future__ import annotations

import httpx
import pytest

from delivery_intelligence.gitlab.rate_limiter import RateLimiter


def _make_response(
    status_code: int = 200,
    *,
    limit: str | None = None,
    remaining: str | None = None,
    reset_at: str | None = None,
    retry_after: str | None = None,
) -> httpx.Response:
    headers: dict[str, str] = {}
    if limit is not None:
        headers["RateLimit-Limit"] = limit
    if remaining is not None:
        headers["RateLimit-Remaining"] = remaining
    if reset_at is not None:
        headers["RateLimit-Reset"] = reset_at
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return httpx.Response(status_code, json={}, headers=headers)


def test_update_parses_headers() -> None:
    rl = RateLimiter()
    response = _make_response(200, limit="1000", remaining="500", reset_at="9999999999")
    rl.update(response)
    state = rl.get_state()
    assert state.limit == 1000
    assert state.remaining == 500
    assert state.reset_at == 9999999999.0


def test_update_parses_429_retry_after() -> None:
    rl = RateLimiter()
    response = _make_response(429, retry_after="30")
    rl.update(response)
    state = rl.get_state()
    assert state.retry_after == 30.0


def test_update_missing_headers_does_not_crash() -> None:
    rl = RateLimiter()
    response = _make_response(200)
    rl.update(response)
    state = rl.get_state()
    assert state.limit is None
    assert state.remaining is None


async def test_wait_if_needed_false_when_healthy() -> None:
    rl = RateLimiter()
    response = _make_response(200, remaining="100")
    rl.update(response)
    result = await rl.wait_if_needed()
    assert result is False
    assert rl.get_wait_count() == 0


async def test_wait_if_needed_sleeps_on_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def mock_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("delivery_intelligence.gitlab.rate_limiter.asyncio.sleep", mock_sleep)

    rl = RateLimiter()
    response = _make_response(429, retry_after="5")
    rl.update(response)
    result = await rl.wait_if_needed()
    assert result is True
    assert slept == [5.0]
    assert rl.get_wait_count() == 1


async def test_wait_if_needed_sleeps_when_remaining_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def mock_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("delivery_intelligence.gitlab.rate_limiter.asyncio.sleep", mock_sleep)

    rl = RateLimiter()
    import time
    future_reset = str(time.time() + 10)
    response = _make_response(200, remaining="0", reset_at=future_reset)
    rl.update(response)
    result = await rl.wait_if_needed()
    assert result is True
    assert len(slept) == 1
    assert slept[0] > 0


async def test_preemptive_throttle_below_buffer(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def mock_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("delivery_intelligence.gitlab.rate_limiter.asyncio.sleep", mock_sleep)

    rl = RateLimiter(buffer_threshold=5)
    response = _make_response(200, remaining="3")
    rl.update(response)
    result = await rl.wait_if_needed()
    assert result is True
    assert rl.get_wait_count() == 1


def test_is_rate_limited_false_normally() -> None:
    rl = RateLimiter()
    assert rl.is_rate_limited() is False


def test_is_rate_limited_true_when_remaining_zero() -> None:
    rl = RateLimiter()
    response = _make_response(200, remaining="0")
    rl.update(response)
    assert rl.is_rate_limited() is True
