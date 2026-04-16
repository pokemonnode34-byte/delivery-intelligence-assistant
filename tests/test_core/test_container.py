"""Tests for the dependency injection container."""

from __future__ import annotations

import pytest

from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.auth import GitLabAuth
from delivery_intelligence.core.container import Container, create_container


def test_create_container_returns_container() -> None:
    settings = AppSettings()
    container = create_container(settings)
    assert isinstance(container, Container)


def test_get_settings_before_initialize() -> None:
    settings = AppSettings()
    container = create_container(settings)
    result = container.get_settings()
    assert result is settings


def test_initialize_completes_without_error() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()


def test_get_auth_returns_gitlab_auth() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    auth = container.get_auth()
    assert isinstance(auth, GitLabAuth)


def test_get_logger_returns_logger() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    logger = container.get_logger("test")
    assert logger is not None


def test_get_auth_before_initialize_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_auth()


def test_get_logger_before_initialize_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_logger("test")


def test_shutdown_sets_initialized_false() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    container.shutdown()
    assert container._initialized is False


def test_post_shutdown_get_auth_raises() -> None:
    settings = AppSettings()
    container = create_container(settings)
    container.initialize()
    container.shutdown()
    with pytest.raises(RuntimeError, match="Container not initialized"):
        container.get_auth()


def test_conftest_test_container_fixture(test_container: Container) -> None:
    auth = test_container.get_auth()
    assert isinstance(auth, GitLabAuth)
