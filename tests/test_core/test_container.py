"""Tests for the dependency injection container (Step 8)."""

import pytest

import delivery_intelligence.core.logging as log_module
from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.auth import GitLabAuth
from delivery_intelligence.core.container import Container, create_container


@pytest.fixture(autouse=True)
def reset_logging_state() -> None:
    """Reset logging flag before each test for isolation."""
    log_module._logging_configured = False


# ---------------------------------------------------------------------------
# create_container
# ---------------------------------------------------------------------------


class TestCreateContainer:
    def test_returns_container_instance(self) -> None:
        container = create_container(AppSettings())
        assert isinstance(container, Container)

    def test_not_initialized_by_default(self) -> None:
        container = create_container(AppSettings())
        assert container._initialized is False


# ---------------------------------------------------------------------------
# Container — before initialize
# ---------------------------------------------------------------------------


class TestContainerBeforeInitialize:
    def test_get_settings_available_immediately(self) -> None:
        settings = AppSettings()
        container = create_container(settings)
        assert container.get_settings() is settings

    def test_get_auth_before_initialize_raises(self) -> None:
        container = create_container(AppSettings())
        with pytest.raises(RuntimeError, match="not initialized"):
            container.get_auth()

    def test_get_logger_before_initialize_raises(self) -> None:
        container = create_container(AppSettings())
        with pytest.raises(RuntimeError, match="not initialized"):
            container.get_logger("test")


# ---------------------------------------------------------------------------
# Container — after initialize
# ---------------------------------------------------------------------------


class TestContainerAfterInitialize:
    def test_initialize_completes_without_error(self) -> None:
        container = create_container(AppSettings())
        container.initialize()  # must not raise
        assert container._initialized is True

    def test_get_auth_returns_gitlab_auth(self) -> None:
        container = create_container(AppSettings())
        container.initialize()
        auth = container.get_auth()
        assert isinstance(auth, GitLabAuth)

    def test_get_logger_returns_logger(self) -> None:
        container = create_container(AppSettings())
        container.initialize()
        logger = container.get_logger("test_module")
        assert logger is not None

    def test_get_settings_still_works_after_initialize(self) -> None:
        settings = AppSettings()
        container = create_container(settings)
        container.initialize()
        assert container.get_settings() is settings

    def test_initialize_twice_is_safe(self) -> None:
        """initialize() is safe to call twice because setup_logging is idempotent."""
        container = create_container(AppSettings())
        container.initialize()
        container.initialize()  # second call must not raise
        assert container._initialized is True


# ---------------------------------------------------------------------------
# shutdown
# ---------------------------------------------------------------------------


class TestContainerShutdown:
    def test_shutdown_sets_not_initialized(self) -> None:
        container = create_container(AppSettings())
        container.initialize()
        assert container._initialized is True
        container.shutdown()
        assert container._initialized is False

    def test_get_auth_after_shutdown_raises(self) -> None:
        container = create_container(AppSettings())
        container.initialize()
        container.shutdown()
        with pytest.raises(RuntimeError, match="not initialized"):
            container.get_auth()
