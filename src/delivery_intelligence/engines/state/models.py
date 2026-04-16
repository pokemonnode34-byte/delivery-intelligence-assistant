"""State domain models for the project state engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

from delivery_intelligence.models.contributor import Contributor
from delivery_intelligence.models.issue import Issue
from delivery_intelligence.models.merge_request import MergeRequest
from delivery_intelligence.models.milestone import Milestone
from delivery_intelligence.models.pipeline import Pipeline
from delivery_intelligence.models.project import Project


class StateCompleteness(str, Enum):
    """State completeness values."""

    FULL = "FULL"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"


class StateHealth(str, Enum):
    """State health values."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class RelationshipType(str, Enum):
    """Supported relationship kinds between entities."""

    BELONGS_TO_MILESTONE = "BELONGS_TO_MILESTONE"
    ASSIGNED_TO = "ASSIGNED_TO"
    TRIGGERS_PIPELINE = "TRIGGERS_PIPELINE"
    REVIEWED_BY = "REVIEWED_BY"


class UpdateSource(str, Enum):
    """Source of state updates."""

    FULL_REFRESH = "FULL_REFRESH"
    WEBHOOK = "WEBHOOK"
    INCREMENTAL_FETCH = "INCREMENTAL_FETCH"


@dataclass
class EntityRelationship:
    source_type: str
    source_id: int
    target_type: str
    target_id: int
    relationship_type: RelationshipType
    project_id: int


@dataclass
class RelationshipIndex:
    by_source: dict[tuple[str, int], list[EntityRelationship]] = field(default_factory=dict)
    by_target: dict[tuple[str, int], list[EntityRelationship]] = field(default_factory=dict)
    by_type: dict[RelationshipType, list[EntityRelationship]] = field(default_factory=dict)

    def get_relationships_from(self, entity_type: str, entity_id: int) -> list[EntityRelationship]:
        return self.by_source.get((entity_type, entity_id), [])

    def get_relationships_to(self, entity_type: str, entity_id: int) -> list[EntityRelationship]:
        return self.by_target.get((entity_type, entity_id), [])

    def get_by_type(self, rel_type: RelationshipType) -> list[EntityRelationship]:
        return self.by_type.get(rel_type, [])

    def count(self) -> int:
        return sum(len(relationships) for relationships in self.by_source.values())


@dataclass
class StateMetadata:
    project_id: int
    completeness: StateCompleteness = StateCompleteness.EMPTY
    health: StateHealth = StateHealth.UNKNOWN
    last_refresh_at: datetime | None = None
    last_updated_at: datetime | None = None
    entity_counts: dict[str, int] = field(default_factory=dict)
    fetch_failures: int = 0


@dataclass
class IngestSummary:
    project_id: int
    source: UpdateSource
    started_at: datetime
    completed_at: datetime
    entities_loaded: dict[str, int]
    entities_failed: dict[str, int]
    dropped_records: list[str] = field(default_factory=list)
    relationships_extracted: int = 0
    consistency_issues: int = 0


@dataclass
class UpdateResult:
    project_id: int
    entity_type: str
    entity_id: int
    applied: bool
    reason: str
    source: UpdateSource = UpdateSource.WEBHOOK


@dataclass
class ConsistencyIssue:
    severity: Literal["WARNING", "ERROR"]
    check_name: str
    entity_type: str | None
    entity_id: int | None
    description: str
    recommendation: str


@dataclass
class ConsistencyReport:
    project_id: int
    generated_at: datetime
    issues: list[ConsistencyIssue] = field(default_factory=list)
    is_healthy: bool = True

    def __post_init__(self) -> None:
        self.is_healthy = not any(issue.severity == "ERROR" for issue in self.issues)


@dataclass
class ProjectState:
    project_id: int
    project: Project | None = None
    issues: dict[int, Issue] = field(default_factory=dict)
    merge_requests: dict[int, MergeRequest] = field(default_factory=dict)
    pipelines: dict[int, Pipeline] = field(default_factory=dict)
    milestones: dict[int, Milestone] = field(default_factory=dict)
    contributors: dict[int, Contributor] = field(default_factory=dict)
    relationship_index: RelationshipIndex = field(default_factory=RelationshipIndex)
    metadata: StateMetadata = field(init=False)

    def __post_init__(self) -> None:
        self.metadata = StateMetadata(project_id=self.project_id)
