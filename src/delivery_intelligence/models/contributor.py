"""Contributor domain model."""

from __future__ import annotations

from typing import Optional

from delivery_intelligence.models.base import BaseEntity


class Contributor(BaseEntity):
    """Normalized representation of a GitLab project member/contributor."""

    id: int
    username: str
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    web_url: Optional[str] = None
    is_active: bool = True
