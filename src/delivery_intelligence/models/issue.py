"""Issue domain model."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import Field

from delivery_intelligence.models.base import BaseEntity, EntityStatus, Priority, UTCDatetime


class Issue(BaseEntity):
    """Normalized representation of a GitLab issue."""

    id: int
    iid: int
    project_id: int
    title: str
    description: Optional[str] = None
    state: EntityStatus
    priority: Priority = Priority.NONE
    labels: list[str] = Field(default_factory=list)
    assignee_ids: list[int] = Field(default_factory=list)
    author_id: int
    milestone_id: Optional[int] = None
    due_date: Optional[date] = None
    weight: Optional[int] = None
    time_estimate: Optional[int] = None
    time_spent: Optional[int] = None
    blocking_issues_count: int = 0
    created_at: UTCDatetime
    updated_at: UTCDatetime
    closed_at: Optional[UTCDatetime] = None
