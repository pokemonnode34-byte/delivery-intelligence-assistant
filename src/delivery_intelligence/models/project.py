"""Project domain model."""

from delivery_intelligence.models.base import BaseEntity, UTCDatetime


class Project(BaseEntity):
    """Represents a GitLab project."""

    id: int
    name: str
    path_with_namespace: str
    description: str | None = None
    web_url: str
    default_branch: str = "main"
    visibility: str
    created_at: UTCDatetime
    updated_at: UTCDatetime
    last_activity_at: UTCDatetime | None = None
