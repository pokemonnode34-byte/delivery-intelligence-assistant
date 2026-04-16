"""Tests for GitLab API authentication module."""

from __future__ import annotations

from pydantic import SecretStr

from delivery_intelligence.config.settings import GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth


def test_create_auth_from_settings() -> None:
    settings = GitLabSettings(
        url="https://gitlab.example.com",
        token=SecretStr("my-token"),
        api_version="v4",
    )
    auth = create_auth(settings)
    assert isinstance(auth, GitLabAuth)


def test_get_headers_returns_correct_token() -> None:
    auth = GitLabAuth(token=SecretStr("real-token"), url="https://gitlab.example.com")
    headers = auth.get_headers()
    assert headers == {"PRIVATE-TOKEN": "real-token"}


def test_get_base_url_assembles_correctly() -> None:
    auth = GitLabAuth(token=SecretStr("t"), url="https://gitlab.example.com")
    assert auth.get_base_url() == "https://gitlab.example.com/api/v4"


def test_get_base_url_handles_trailing_slash() -> None:
    auth = GitLabAuth(token=SecretStr("t"), url="https://gitlab.example.com/")
    assert auth.get_base_url() == "https://gitlab.example.com/api/v4"


def test_get_base_url_respects_api_version() -> None:
    auth = GitLabAuth(token=SecretStr("t"), url="https://gitlab.example.com", api_version="v5")
    assert auth.get_base_url() == "https://gitlab.example.com/api/v5"


def test_validate_returns_true_for_valid_credentials() -> None:
    auth = GitLabAuth(token=SecretStr("valid-token"), url="https://gitlab.example.com")
    assert auth.validate() is True


def test_validate_returns_false_for_empty_token() -> None:
    auth = GitLabAuth(token=SecretStr(""), url="https://gitlab.example.com")
    assert auth.validate() is False


def test_repr_never_exposes_token() -> None:
    auth = GitLabAuth(token=SecretStr("super-secret"), url="https://gitlab.example.com")
    assert "super-secret" not in repr(auth)
    assert "super-secret" not in str(auth)
    assert "****" in repr(auth)


def test_repr_includes_url_and_api_version() -> None:
    auth = GitLabAuth(token=SecretStr("t"), url="https://gitlab.example.com")
    r = repr(auth)
    assert "https://gitlab.example.com" in r
    assert "v4" in r
