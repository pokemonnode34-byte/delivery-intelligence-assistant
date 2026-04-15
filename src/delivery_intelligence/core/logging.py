"""Structured logging setup for Delivery Intelligence.

All modules must obtain loggers via :func:`get_logger` and log using
structlog's key-value style.  Plain f-strings in log calls are prohibited.
"""

import logging
from typing import Any

import structlog
from structlog.types import EventDict

from delivery_intelligence.config.settings import LoggingSettings

_logging_configured: bool = False

_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {"token", "password", "secret", "authorization", "credential"}
)


def _redact_sensitive_fields(
    logger: Any,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Replace values of sensitive keys with a redaction marker."""
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in _SENSITIVE_KEYS):
            event_dict[key] = "****REDACTED****"
    return event_dict


def setup_logging(settings: LoggingSettings, force: bool = False) -> None:
    """Configure structlog and the stdlib root logger.

    Idempotent: calling this function more than once has no effect unless
    ``force=True`` is passed.  Use ``force=True`` in tests to reinitialise
    between test cases.
    """
    global _logging_configured

    if _logging_configured and not force:
        return

    log_level = getattr(logging, settings.level)

    shared: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_sensitive_fields,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.format == "json":
        processors: list[Any] = shared + [structlog.processors.JSONRenderer()]
    else:
        processors = [
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_sensitive_fields,
            structlog.dev.ConsoleRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    # Configure the stdlib root logger so third-party library logs also use
    # the correct level.
    root = logging.getLogger()
    if force:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        root.addHandler(handler)
    root.setLevel(log_level)

    _logging_configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger with ``logger_name`` pre-attached.

    Does not cache logger instances; structlog manages that internally.
    """
    return structlog.get_logger().bind(logger_name=name)
