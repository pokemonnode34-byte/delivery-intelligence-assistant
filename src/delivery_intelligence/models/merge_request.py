"""Merge request domain model."""

from pydantic import Field

from delivery_intelligence.models.base import BaseEntity, EntityStatus, UTCDatetime


class MergeRequest(BaseEntity):
    """Represents a GitLab merge request."""

    id: int
    iid: int
    project_id: int
    title: str
    description: str | None = None
    state: EntityStatus
    source_branch: str
    target_branch: str
    author_id: int
    assignee_ids: list[int] = Field(default_factory=list)
    reviewer_ids: list[int] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    milestone_id: int | None = None
    pipeline_id: int | None = None
    has_conflicts: bool = False
    draft: bool = False
    changes_count: int | None = None
    created_at: UTCDatetime
    updated_at: UTCDatetime
    merged_at: UTCDatetime | None = None
    closed_at: UTCDatetime | None = None
