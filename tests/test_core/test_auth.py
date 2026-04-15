"""Tests for GitLab API authentication (Step 5)."""

from pydantic import SecretStr

from delivery_intelligence.config.settings import GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth


# ---------------------------------------------------------------------------
# GitLabAuth
# ---------------------------------------------------------------------------


class TestGitLabAuth:
    def test_construction(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("mytoken"), url="https://gitlab.example.com"
        )
        assert auth.validate() is True

    def test_get_headers_returns_private_token(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("mytoken"), url="https://gitlab.example.com"
        )
        assert auth.get_headers() == {"PRIVATE-TOKEN": "mytoken"}

    def test_get_base_url_default_version(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("t"),
            url="https://gitlab.example.com",
            api_version="v4",
        )
        assert auth.get_base_url() == "https://gitlab.example.com/api/v4"

    def test_get_base_url_strips_trailing_slash(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("t"),
            url="https://gitlab.example.com/",
            api_version="v4",
        )
        assert auth.get_base_url() == "https://gitlab.example.com/api/v4"

    def test_get_base_url_custom_version(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("t"),
            url="https://gitlab.example.com",
            api_version="v5",
        )
        assert auth.get_base_url() == "https://gitlab.example.com/api/v5"

    def test_validate_empty_token_returns_false(self) -> None:
        auth = GitLabAuth(token=SecretStr(""), url="https://gitlab.example.com")
        assert auth.validate() is False

    def test_validate_empty_url_returns_false(self) -> None:
        auth = GitLabAuth(token=SecretStr("mytoken"), url="")
        assert auth.validate() is False

    def test_validate_valid_credentials_returns_true(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("realtoken"), url="https://gitlab.example.com"
        )
        assert auth.validate() is True

    def test_repr_masks_token(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("supersecret"), url="https://gitlab.example.com"
        )
        r = repr(auth)
        assert "supersecret" not in r
        assert "****" in r

    def test_str_masks_token(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("supersecret"), url="https://gitlab.example.com"
        )
        assert "supersecret" not in str(auth)

    def test_repr_contains_url_and_version(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("t"),
            url="https://gitlab.example.com",
            api_version="v4",
        )
        r = repr(auth)
        expected = "GitLabAuth(url=https://gitlab.example.com, api_version=v4, token=****)"
        assert r == expected

    def test_str_equals_repr(self) -> None:
        auth = GitLabAuth(
            token=SecretStr("t"), url="https://gitlab.example.com"
        )
        assert str(auth) == repr(auth)


# ---------------------------------------------------------------------------
# create_auth
# ---------------------------------------------------------------------------


class TestCreateAuth:
    def test_creates_auth_from_settings(self) -> None:
        settings = GitLabSettings(
            url="https://gitlab.example.com", token=SecretStr("mytoken")
        )
        auth = create_auth(settings)
        assert isinstance(auth, GitLabAuth)

    def test_auth_uses_settings_url(self) -> None:
        settings = GitLabSettings(
            url="https://my.gitlab.com", token=SecretStr("tok")
        )
        auth = create_auth(settings)
        assert auth.get_base_url() == "https://my.gitlab.com/api/v4"

    def test_auth_uses_settings_api_version(self) -> None:
        settings = GitLabSettings(
            url="https://gitlab.example.com",
            token=SecretStr("tok"),
            api_version="v4",
        )
        auth = create_auth(settings)
        assert "v4" in auth.get_base_url()

    def test_auth_validates_ok(self) -> None:
        settings = GitLabSettings(
            url="https://gitlab.example.com", token=SecretStr("realtoken")
        )
        auth = create_auth(settings)
        assert auth.validate() is True
