"""Project domain model."""

from __future__ import annotations

from typing import Optional

from delivery_intelligence.models.base import BaseEntity, UTCDatetime


class Project(BaseEntity):
    """Normalized representation of a GitLab project."""

    id: int
    name: str
    path_with_namespace: str
    description: Optional[str] = None
    web_url: str
    default_branch: str = "main"
    visibility: str
    created_at: UTCDatetime
    updated_at: UTCDatetime
    last_activity_at: Optional[UTCDatetime] = None
