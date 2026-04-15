"""Shared pytest fixtures for the Delivery Intelligence test suite."""

import pytest

import delivery_intelligence.core.logging as log_module
from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.container import Container, create_container


@pytest.fixture
def test_settings() -> AppSettings:
    """Return AppSettings with development defaults."""
    return AppSettings()


@pytest.fixture
def test_container(test_settings: AppSettings) -> Container:
    """Return an initialised Container built from development defaults."""
    log_module._logging_configured = False
    container = create_container(test_settings)
    container.initialize()
    return container
