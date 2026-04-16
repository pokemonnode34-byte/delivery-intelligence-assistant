"""Base classes, enums, and shared types for domain models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator


def _validate_utc_datetime(value: Any) -> datetime:
    """Validate and normalize datetime to UTC.

    - Rejects naive datetimes.
    - Normalizes timezone-aware non-UTC datetimes to UTC.
    - Passes through UTC datetimes unchanged.
    """
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            value = datetime.fromisoformat(normalized)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot parse datetime: {value!r}") from e

    if not isinstance(value, datetime):
        raise ValueError(f"Expected datetime, got {type(value).__name__}")

    if value.tzinfo is None:
        raise ValueError(
            f"Naive datetime rejected: {value!r}. All datetimes must be timezone-aware UTC."
        )

    if value.tzinfo != timezone.utc and value.utcoffset() != timezone.utc.utcoffset(None):
        value = value.astimezone(timezone.utc)

    return value


UTCDatetime = Annotated[datetime, BeforeValidator(_validate_utc_datetime)]


class BaseEntity(BaseModel):
    """Base class for all domain entities with shared Pydantic config."""

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "frozen": True,
    }


class EntityStatus(StrEnum):
    """Status values for GitLab entities."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"
    LOCKED = "LOCKED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"


class Priority(StrEnum):
    """Priority levels for issues and work items."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class RiskLevel(StrEnum):
    """Risk levels for project assessment."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"
