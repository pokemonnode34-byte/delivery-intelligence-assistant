"""Pipeline domain model and status enum."""

from __future__ import annotations

from enum import StrEnum
from typing import Optional

from delivery_intelligence.models.base import BaseEntity, UTCDatetime


class PipelineStatus(StrEnum):
    """Pipeline execution status values."""

    CREATED = "CREATED"
    WAITING_FOR_RESOURCE = "WAITING_FOR_RESOURCE"
    PREPARING = "PREPARING"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    SKIPPED = "SKIPPED"
    MANUAL = "MANUAL"
    SCHEDULED = "SCHEDULED"


class Pipeline(BaseEntity):
    """Normalized representation of a GitLab pipeline."""

    id: int
    project_id: int
    ref: str
    sha: str
    status: PipelineStatus
    source: str
    duration: Optional[int] = None
    queued_duration: Optional[int] = None
    started_at: Optional[UTCDatetime] = None
    finished_at: Optional[UTCDatetime] = None
    created_at: UTCDatetime
    updated_at: UTCDatetime
