"""Milestone domain model and state enumeration."""

from datetime import date
from enum import Enum

from delivery_intelligence.models.base import BaseEntity, UTCDatetime


class MilestoneState(str, Enum):
    """Lifecycle state of a GitLab milestone."""

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class Milestone(BaseEntity):
    """Represents a GitLab project milestone."""

    id: int
    iid: int
    project_id: int
    title: str
    description: str | None = None
    state: MilestoneState
    due_date: date | None = None
    start_date: date | None = None
    expired: bool = False
    created_at: UTCDatetime
    updated_at: UTCDatetime
