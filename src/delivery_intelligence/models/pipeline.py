"""Pipeline domain model and status enumeration."""

from enum import Enum

from delivery_intelligence.models.base import BaseEntity, UTCDatetime


class PipelineStatus(str, Enum):
    """Lifecycle status values for a CI/CD pipeline."""

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
    """Represents a GitLab CI/CD pipeline run."""

    id: int
    project_id: int
    ref: str
    sha: str
    status: PipelineStatus
    source: str
    duration: int | None = None
    queued_duration: int | None = None
    started_at: UTCDatetime | None = None
    finished_at: UTCDatetime | None = None
    created_at: UTCDatetime
    updated_at: UTCDatetime
