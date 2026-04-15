"""Contributor domain model."""

from delivery_intelligence.models.base import BaseEntity


class Contributor(BaseEntity):
    """Represents a GitLab user who contributes to a project.

    This model has no datetime fields but still extends :class:`BaseEntity`
    for consistent configuration across all domain models.
    """

    id: int
    username: str
    name: str
    email: str | None = None
    avatar_url: str | None = None
    web_url: str | None = None
    is_active: bool = True
