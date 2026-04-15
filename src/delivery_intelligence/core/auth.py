"""GitLab API authentication scaffolding.

Provides :class:`GitLabAuth` for building authenticated request headers
and the correct API base URL.  No network calls are made here; that
belongs to the GitLab client in Phase 1.
"""

from pydantic import SecretStr

from delivery_intelligence.config.settings import GitLabSettings


class GitLabAuth:
    """Holds GitLab credentials and assembles connection context.

    The token is never stored in plain text and never appears in
    ``repr()`` or ``str()`` output.
    """

    def __init__(
        self,
        token: SecretStr,
        url: str,
        api_version: str = "v4",
    ) -> None:
        self._token: SecretStr = token
        self._url: str = url.rstrip("/")
        self._api_version: str = api_version

    def get_headers(self) -> dict[str, str]:
        """Return HTTP headers required to authenticate with the GitLab API."""
        return {"PRIVATE-TOKEN": self._token.get_secret_value()}

    def get_base_url(self) -> str:
        """Return the full API base URL (e.g. ``https://gitlab.example.com/api/v4``)."""
        return f"{self._url}/api/{self._api_version}"

    def validate(self) -> bool:
        """Return True when both the token and URL are non-empty.

        Does not make any network requests.
        """
        return bool(self._token.get_secret_value()) and bool(self._url)

    def __repr__(self) -> str:
        return (
            f"GitLabAuth(url={self._url}, "
            f"api_version={self._api_version}, "
            "token=****)"
        )

    def __str__(self) -> str:
        return self.__repr__()


def create_auth(settings: GitLabSettings) -> GitLabAuth:
    """Construct a :class:`GitLabAuth` from :class:`GitLabSettings`."""
    return GitLabAuth(
        token=settings.token,
        url=settings.url,
        api_version=settings.api_version,
    )
