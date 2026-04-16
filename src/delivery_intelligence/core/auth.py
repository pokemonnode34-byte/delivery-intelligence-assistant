"""GitLab API authentication module."""

from __future__ import annotations

from pydantic import SecretStr

from delivery_intelligence.config.settings import GitLabSettings


class GitLabAuth:
    """Immutable GitLab API authentication container.

    Holds credentials and base URL assembly logic.
    The token is never stored as plain text.
    """

    def __init__(self, token: SecretStr, url: str, api_version: str = "v4") -> None:
        self._token = token
        self._url = url.rstrip("/")
        self._api_version = api_version

    @property
    def url(self) -> str:
        """Base GitLab instance URL (no API path)."""
        return self._url

    @property
    def api_version(self) -> str:
        """API version string."""
        return self._api_version

    def get_headers(self) -> dict[str, str]:
        """Return authentication headers with the plain token value."""
        return {"PRIVATE-TOKEN": self._token.get_secret_value()}

    def get_base_url(self) -> str:
        """Return full API base URL assembled from url and api_version."""
        return f"{self._url}/api/{self._api_version}"

    def validate(self) -> bool:
        """Return True if token and URL are non-empty. Does not make network calls."""
        return bool(self._token.get_secret_value()) and bool(self._url)

    def __repr__(self) -> str:
        return f"GitLabAuth(url={self._url}, api_version={self._api_version}, token=****)"

    def __str__(self) -> str:
        return self.__repr__()


def create_auth(settings: GitLabSettings) -> GitLabAuth:
    """Factory function that constructs GitLabAuth from GitLabSettings."""
    return GitLabAuth(
        token=settings.token,
        url=settings.url,
        api_version=settings.api_version,
    )
