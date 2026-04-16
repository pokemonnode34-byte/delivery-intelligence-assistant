"""Pagination engine for GitLab API list endpoints."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable
from urllib.parse import parse_qs, urlparse

import httpx

from delivery_intelligence.core.logging import get_logger

_logger = get_logger("gitlab.pagination")

_PAGINATION_SAFETY_CEILING = 1000

RequestFn = Callable[[str, str, "dict[str, Any] | None"], Awaitable[httpx.Response]]


@dataclass
class PaginatedResponse:
    """Parsed pagination metadata from GitLab response headers."""

    items: list[dict[str, Any]]
    page: int
    per_page: int
    total: int | None
    total_pages: int | None
    next_page: int | None
    next_url: str | None
    has_next: bool


def _parse_link_header_next(link_header: str) -> str | None:
    """Extract the 'next' URL from a Link header value."""
    for part in link_header.split(","):
        url_match = re.match(r'\s*<([^>]+)>', part)
        rel_match = re.search(r'rel="([^"]+)"', part)
        if url_match and rel_match and rel_match.group(1) == "next":
            return url_match.group(1)
    return None


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_pagination_headers(response: httpx.Response) -> PaginatedResponse:
    """Extract pagination metadata from GitLab response headers and parse body as JSON list."""
    headers = response.headers

    try:
        items: list[dict[str, Any]] = response.json()
        if not isinstance(items, list):
            items = []
    except Exception:
        items = []

    page = _parse_optional_int(headers.get("x-page")) or 1
    per_page = _parse_optional_int(headers.get("x-per-page")) or 100
    total = _parse_optional_int(headers.get("x-total"))
    total_pages = _parse_optional_int(headers.get("x-total-pages"))
    next_page = _parse_optional_int(headers.get("x-next-page"))

    link_header = headers.get("link") or headers.get("Link")
    next_url: str | None = None
    if link_header:
        next_url = _parse_link_header_next(link_header)

    has_next = next_page is not None or next_url is not None

    return PaginatedResponse(
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        next_page=next_page,
        next_url=next_url,
        has_next=has_next,
    )


async def paginate(
    request_fn: RequestFn,
    path: str,
    params: dict[str, Any] | None = None,
    per_page: int = 100,
    max_pages: int | None = None,
) -> AsyncIterator[list[dict[str, Any]]]:
    """Async generator that yields one page of items at a time.

    Handles both offset pagination (x-next-page header) and keyset pagination
    (Link rel=next header). Never imports or references GitLabClient, retry,
    or rate-limit modules directly.
    """
    page_count = 0
    current_path: str | None = path
    current_params: dict[str, Any] | None = {**(params or {}), "page": 1, "per_page": per_page}

    while current_path is not None:
        if max_pages is not None and page_count >= max_pages:
            break
        if page_count >= _PAGINATION_SAFETY_CEILING:
            _logger.warning(
                "pagination_safety_ceiling_reached",
                path=path,
                page_count=page_count,
                ceiling=_PAGINATION_SAFETY_CEILING,
            )
            break

        response = await request_fn("GET", current_path, current_params)
        page_result = parse_pagination_headers(response)
        page_count += 1

        if page_result.items:
            yield page_result.items

        if not page_result.has_next:
            break

        if page_result.next_url is not None:
            # Keyset pagination: extract relative path and params from absolute URL
            parsed = urlparse(page_result.next_url)
            current_path = parsed.path
            qs = parse_qs(parsed.query, keep_blank_values=True)
            current_params = {k: v[0] for k, v in qs.items()}
        elif page_result.next_page is not None:
            current_params = {**(params or {}), "page": page_result.next_page, "per_page": per_page}
        else:
            break


async def paginate_all(
    request_fn: RequestFn,
    path: str,
    params: dict[str, Any] | None = None,
    per_page: int = 100,
    max_pages: int | None = None,
) -> list[dict[str, Any]]:
    """Collect all pages into a flat list of items."""
    all_items: list[dict[str, Any]] = []
    async for page_items in paginate(request_fn, path, params, per_page, max_pages):
        all_items.extend(page_items)
    return all_items
