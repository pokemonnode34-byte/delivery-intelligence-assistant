"""Shared fixtures for GitLab tests."""

from __future__ import annotations

import pytest
import respx
from pydantic import SecretStr

from delivery_intelligence.config.settings import GitLabSettings
from delivery_intelligence.core.auth import GitLabAuth, create_auth


@pytest.fixture
def gitlab_settings() -> GitLabSettings:
    return GitLabSettings(
        url="https://gitlab.example.com",
        token=SecretStr("test-token"),
        api_version="v4",
        timeout=10,
        max_retries=2,
        per_page=20,
    )


@pytest.fixture
def gitlab_auth(gitlab_settings: GitLabSettings) -> GitLabAuth:
    return create_auth(gitlab_settings)


@pytest.fixture
def mock_transport() -> respx.MockTransport:
    return respx.MockTransport()
