"""Structured logging setup for Delivery Intelligence."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from delivery_intelligence.config.settings import LoggingSettings

_logging_configured: bool = False

_SENSITIVE_KEYS = {"token", "password", "secret", "authorization", "credential"}


def _redact_sensitive_fields(
    logger: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that redacts sensitive field values."""
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in _SENSITIVE_KEYS):
            event_dict[key] = "****REDACTED****"
    return event_dict


def setup_logging(settings: LoggingSettings, force: bool = False) -> None:
    """Configure structlog and stdlib logging.

    Idempotent by default. Use force=True to re-initialize (e.g., in tests).
    """
    global _logging_configured

    if _logging_configured and not force:
        structlog.get_logger("logging").debug("logging_already_configured")
        return

    log_level = getattr(logging, settings.level, logging.INFO)

    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_sensitive_fields,
    ]

    if settings.format == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    # Configure stdlib root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if force or not root_logger.handlers:
        # Remove existing handlers to avoid duplicates on force re-init
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        root_logger.addHandler(handler)

    _logging_configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger with the logger_name pre-attached."""
    return structlog.get_logger(name).bind(logger_name=name)
