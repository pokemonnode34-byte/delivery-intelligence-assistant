"""Shared test fixtures for the delivery_intelligence test suite."""

from __future__ import annotations

import pytest

from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.container import Container, create_container


@pytest.fixture
def test_settings() -> AppSettings:
    """Return AppSettings with development defaults for testing."""
    return AppSettings()


@pytest.fixture
def test_container(test_settings: AppSettings) -> Container:
    """Return an initialized Container with test settings."""
    container = create_container(test_settings)
    container.initialize()
    return container
