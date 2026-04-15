"""Shared base types, mixins, and enumerations for domain models.

All domain models extend :class:`BaseEntity`.  Every ``datetime`` field
must use the :data:`UTCDatetime` annotated type to enforce timezone-aware
UTC datetimes.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator


def _validate_utc_datetime(v: Any) -> datetime:
    """Validate and normalise a datetime value to UTC.

    - Strings are parsed via ``datetime.fromisoformat``.
    - Naive datetimes (no timezone) are rejected.
    - Timezone-aware non-UTC datetimes are converted to UTC.
    - UTC datetimes pass through unchanged.
    """
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v)
        except ValueError as exc:
            raise ValueError(f"Invalid datetime string: '{v}'") from exc
    if not isinstance(v, datetime):
        raise ValueError(
            f"Expected a datetime instance, got {type(v).__name__}"
        )
    if v.tzinfo is None:
        raise ValueError(
            "Datetime must be timezone-aware (UTC). "
            "Naive datetimes are not allowed."
        )
    return v.astimezone(timezone.utc)


UTCDatetime = Annotated[datetime, BeforeValidator(_validate_utc_datetime)]
"""A ``datetime`` field that is always stored as UTC.

Naive datetimes raise ``ValidationError``.  Timezone-aware datetimes are
normalised to UTC automatically.
"""


class BaseEntity(BaseModel):
    """Shared Pydantic config for all domain models.

    Models are immutable (``frozen=True``).  Mutations happen by creating
    new instances with ``model.model_copy(update={...})``.
    """

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "frozen": True,
    }


class TimestampMixin(BaseModel):
    """Provides standard ``created_at`` and ``updated_at`` timestamp fields."""

    created_at: UTCDatetime
    updated_at: UTCDatetime


class EntityStatus(str, Enum):
    """General lifecycle status for issues, merge requests, etc."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"
    LOCKED = "LOCKED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"


class Priority(str, Enum):
    """Work-item priority levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class RiskLevel(str, Enum):
    """Risk severity levels for delivery analysis."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"
