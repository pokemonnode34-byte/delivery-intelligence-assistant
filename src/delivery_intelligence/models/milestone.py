"""Milestone domain model and state enum."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Optional

from delivery_intelligence.models.base import BaseEntity, UTCDatetime


class MilestoneState(StrEnum):
    """Milestone lifecycle state values."""

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class Milestone(BaseEntity):
    """Normalized representation of a GitLab milestone."""

    id: int
    iid: int
    project_id: int
    title: str
    description: Optional[str] = None
    state: MilestoneState
    due_date: Optional[date] = None
    start_date: Optional[date] = None
    expired: bool = False
    created_at: UTCDatetime
    updated_at: UTCDatetime
