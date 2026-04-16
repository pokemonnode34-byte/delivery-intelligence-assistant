"""MergeRequest domain model."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from delivery_intelligence.models.base import BaseEntity, EntityStatus, UTCDatetime


class MergeRequest(BaseEntity):
    """Normalized representation of a GitLab merge request."""

    id: int
    iid: int
    project_id: int
    title: str
    description: Optional[str] = None
    state: EntityStatus
    source_branch: str
    target_branch: str
    author_id: int
    assignee_ids: list[int] = Field(default_factory=list)
    reviewer_ids: list[int] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    milestone_id: Optional[int] = None
    pipeline_id: Optional[int] = None
    has_conflicts: bool = False
    draft: bool = False
    changes_count: Optional[int] = None
    created_at: UTCDatetime
    updated_at: UTCDatetime
    merged_at: Optional[UTCDatetime] = None
    closed_at: Optional[UTCDatetime] = None
