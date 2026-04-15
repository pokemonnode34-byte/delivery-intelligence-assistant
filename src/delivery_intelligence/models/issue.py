"""Issue domain model."""

from datetime import date

from pydantic import Field

from delivery_intelligence.models.base import (
    BaseEntity,
    EntityStatus,
    Priority,
    UTCDatetime,
)


class Issue(BaseEntity):
    """Represents a GitLab issue (or future Work Item / Task)."""

    id: int
    iid: int
    project_id: int
    title: str
    description: str | None = None
    state: EntityStatus
    priority: Priority = Priority.NONE
    labels: list[str] = Field(default_factory=list)
    assignee_ids: list[int] = Field(default_factory=list)
    author_id: int
    milestone_id: int | None = None
    due_date: date | None = None
    weight: int | None = None
    time_estimate: int | None = None
    time_spent: int | None = None
    blocking_issues_count: int = 0
    created_at: UTCDatetime
    updated_at: UTCDatetime
    closed_at: UTCDatetime | None = None
