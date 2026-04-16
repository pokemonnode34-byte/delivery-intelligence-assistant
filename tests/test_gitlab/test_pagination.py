"""Tests for pagination engine."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from delivery_intelligence.gitlab.pagination import (
    paginate_all,
    parse_pagination_headers,
)


def _make_response(
    items: list[dict],
    *,
    page: int = 1,
    per_page: int = 3,
    total: int | None = None,
    total_pages: int | None = None,
    next_page: int | None = None,
    next_url: str | None = None,
    status_code: int = 200,
) -> httpx.Response:
    headers: dict[str, str] = {
        "x-page": str(page),
        "x-per-page": str(per_page),
    }
    if total is not None:
        headers["x-total"] = str(total)
    if total_pages is not None:
        headers["x-total-pages"] = str(total_pages)
    if next_page is not None:
        headers["x-next-page"] = str(next_page)
    if next_url is not None:
        headers["link"] = f'<{next_url}>; rel="next"'
    return httpx.Response(status_code, json=items, headers=headers)


async def test_single_page_returns_all_items() -> None:
    async def request_fn(method: str, path: str, params: Any) -> httpx.Response:
        return _make_response([{"id": 1}, {"id": 2}], total=2, total_pages=1)

    results = await paginate_all(request_fn, "/items")
    assert len(results) == 2
    assert results[0]["id"] == 1


async def test_multi_page_offset_pagination() -> None:
    responses = [
        _make_response([{"id": 1}], page=1, total_pages=2, next_page=2),
        _make_response([{"id": 2}], page=2, total_pages=2),
    ]
    call_count = 0

    async def request_fn(method: str, path: str, params: Any) -> httpx.Response:
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        return r

    results = await paginate_all(request_fn, "/items")
    assert len(results) == 2
    assert call_count == 2


async def test_keyset_pagination_via_link_header() -> None:
    responses = [
        _make_response(
            [{"id": 1}],
            next_url="https://gitlab.example.com/api/v4/items?cursor=abc&per_page=1",
        ),
        _make_response([{"id": 2}]),
    ]
    call_count = 0

    async def request_fn(method: str, path: str, params: Any) -> httpx.Response:
        nonlocal call_count
        r = responses[call_count]
        call_count += 1
        return r

    results = await paginate_all(request_fn, "/items", per_page=1)
    assert len(results) == 2


async def test_max_pages_respected() -> None:
    call_count = 0

    async def request_fn(method: str, path: str, params: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _make_response([{"id": call_count}], page=call_count, next_page=call_count + 1)

    results = await paginate_all(request_fn, "/items", max_pages=2)
    assert call_count == 2
    assert len(results) == 2


async def test_missing_pagination_headers_do_not_crash() -> None:
    async def request_fn(method: str, path: str, params: Any) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}])

    results = await paginate_all(request_fn, "/items")
    assert results == [{"id": 1}]


async def test_empty_response() -> None:
    async def request_fn(method: str, path: str, params: Any) -> httpx.Response:
        return httpx.Response(200, json=[])

    results = await paginate_all(request_fn, "/items")
    assert results == []


async def test_safety_ceiling_stops_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    import delivery_intelligence.gitlab.pagination as pagination_module
    monkeypatch.setattr(pagination_module, "_PAGINATION_SAFETY_CEILING", 3)

    call_count = 0

    async def request_fn(method: str, path: str, params: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _make_response([{"id": call_count}], page=call_count, next_page=call_count + 1)

    results = await paginate_all(request_fn, "/items")
    assert call_count == 3
    assert len(results) == 3


def test_parse_pagination_headers_extracts_fields() -> None:
    response = _make_response(
        [{"id": 1}], page=2, per_page=10, total=100, total_pages=10, next_page=3
    )
    result = parse_pagination_headers(response)
    assert result.page == 2
    assert result.per_page == 10
    assert result.total == 100
    assert result.total_pages == 10
    assert result.next_page == 3
    assert result.has_next is True


def test_pagination_has_no_client_import() -> None:
    """Verify pagination module does not import client, retry, or rate_limiter."""
    import ast
    import inspect
    import delivery_intelligence.gitlab.pagination as mod
    source = inspect.getsource(mod)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "client" not in node.module
                assert "retry" not in node.module
                assert "rate_limiter" not in node.module
