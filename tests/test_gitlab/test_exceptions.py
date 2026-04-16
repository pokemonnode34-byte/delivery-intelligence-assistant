"""Tests for GitLab custom exceptions and status mapping."""

import pytest
import httpx

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


def _make_response(
    status_code: int,
    *,
    body: str = "{}",
    headers: dict[str, str] | None = None,
    url: str = "https://gitlab.example.com/api/v4/projects/1/issues",
) -> httpx.Response:
    request = httpx.Request("GET", url)
    return httpx.Response(status_code=status_code, text=body, headers=headers, request=request)


def test_exception_attributes_and_string_representation() -> None:
    error = GitLabAPIError(
        message="failed request",
        status_code=418,
        response_body="nope",
        request_url="https://gitlab.example.com/api/v4/projects/1?token=sensitive",
        correlation_id="abc123",
    )

    assert error.message == "failed request"
    assert error.status_code == 418
    assert error.response_body == "nope"
    assert error.request_url == "https://gitlab.example.com/api/v4/projects/1"
    assert error.correlation_id == "abc123"
    assert str(error) == "GitLabAPIError(418): failed request [correlation_id=abc123]"


def test_raise_for_status_401_raises_auth_error() -> None:
    response = _make_response(401)
    with pytest.raises(GitLabAuthError) as exc_info:
        raise_for_status(response, correlation_id="corr-id")

    assert exc_info.value.status_code == 401
    assert exc_info.value.request_url == "https://gitlab.example.com/api/v4/projects/1/issues"
    assert exc_info.value.correlation_id == "corr-id"


def test_raise_for_status_403_raises_forbidden_error() -> None:
    response = _make_response(403)
    with pytest.raises(GitLabForbiddenError):
        raise_for_status(response)


def test_raise_for_status_404_raises_not_found_error() -> None:
    response = _make_response(404)
    with pytest.raises(GitLabNotFoundError):
        raise_for_status(response)


def test_raise_for_status_429_raises_rate_limit_error_with_retry_after() -> None:
    response = _make_response(
        429,
        headers={"Retry-After": "1.5", "RateLimit-Reset": "1712345678"},
    )
    with pytest.raises(GitLabRateLimitError) as exc_info:
        raise_for_status(response, correlation_id="corr-rate")

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 1.5
    assert exc_info.value.reset_at == 1712345678.0
    assert exc_info.value.correlation_id == "corr-rate"


@pytest.mark.parametrize("status_code", [500, 502, 503])
def test_raise_for_status_server_errors(status_code: int) -> None:
    response = _make_response(status_code)
    with pytest.raises(GitLabServerError) as exc_info:
        raise_for_status(response)

    assert exc_info.value.status_code == status_code


@pytest.mark.parametrize("status_code", [200, 201])
def test_raise_for_status_success_codes_do_not_raise(status_code: int) -> None:
    response = _make_response(status_code)
    raise_for_status(response)


def test_not_found_with_resource_context_is_descriptive() -> None:
    error = GitLabNotFoundError(resource_type="Project", resource_id=123)
    assert error.message == "Project 123 not found."
    assert str(error) == "GitLabAPIError(unknown): Project 123 not found."


def test_connection_error_wraps_cause() -> None:
    cause = httpx.ConnectTimeout("timed out")
    error = GitLabConnectionError(cause=cause, correlation_id="conn-1")

    assert error.cause is cause
    assert error.correlation_id == "conn-1"


def test_exception_str_and_repr_never_include_token_values() -> None:
    token = "glpat-super-secret-token"
    error = GitLabAPIError(
        message=f"failed auth using {token}",
        response_body=f'{{"private_token":"{token}"}}',
        request_url=f"https://gitlab.example.com/api/v4/projects/1?private_token={token}",
    )

    assert token not in str(error)
    assert token not in repr(error)
    assert token not in (error.message or "")
    assert token not in (error.response_body or "")
    assert token not in (error.request_url or "")
