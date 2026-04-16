"""Tests for structured logging setup."""

from __future__ import annotations

import pytest
import structlog

import delivery_intelligence.core.logging as logging_module
from delivery_intelligence.config.settings import LoggingSettings
from delivery_intelligence.core.logging import get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_logging_state() -> None:
    """Reset logging state before each test."""
    logging_module._logging_configured = False
    # Clear structlog cache
    structlog.reset_defaults()
    yield
    logging_module._logging_configured = False
    structlog.reset_defaults()


def test_setup_logging_json_mode_succeeds() -> None:
    settings = LoggingSettings(level="DEBUG", format="json")
    setup_logging(settings)
    assert logging_module._logging_configured is True


def test_setup_logging_console_mode_succeeds() -> None:
    settings = LoggingSettings(level="INFO", format="console")
    setup_logging(settings)
    assert logging_module._logging_configured is True


def test_get_logger_returns_bound_logger() -> None:
    settings = LoggingSettings(level="INFO", format="json")
    setup_logging(settings)
    logger = get_logger("test_module")
    assert logger is not None


def test_setup_logging_idempotent() -> None:
    settings = LoggingSettings(level="INFO", format="json")
    setup_logging(settings)
    setup_logging(settings)  # second call should not raise
    assert logging_module._logging_configured is True


def test_setup_logging_force_reinitializes() -> None:
    settings = LoggingSettings(level="INFO", format="json")
    setup_logging(settings)
    setup_logging(settings, force=True)
    assert logging_module._logging_configured is True


def test_sensitive_field_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    settings = LoggingSettings(level="DEBUG", format="json")
    setup_logging(settings, force=True)
    logger = get_logger("test")
    logger.info("test_event", token="super-secret-value", message="normal")
    captured = capsys.readouterr()
    assert "super-secret-value" not in captured.out
    assert "****REDACTED****" in captured.out


def test_password_field_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    settings = LoggingSettings(level="DEBUG", format="json")
    setup_logging(settings, force=True)
    logger = get_logger("test")
    logger.info("test_event", password="my-password")
    captured = capsys.readouterr()
    assert "my-password" not in captured.out
    assert "****REDACTED****" in captured.out
