"""Tests for state domain models."""

from __future__ import annotations

from datetime import datetime, timezone

from delivery_intelligence.engines.state.models import (
    ConsistencyIssue,
    ConsistencyReport,
    EntityRelationship,
    ProjectState,
    RelationshipIndex,
    RelationshipType,
    StateCompleteness,
    StateHealth,
    UpdateResult,
    UpdateSource,
)


UTC_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_relationship_index_returns_empty_when_no_relationships() -> None:
    index = RelationshipIndex()
    assert index.get_relationships_from("issue", 1) == []
    assert index.get_relationships_to("issue", 1) == []
    assert index.get_by_type(RelationshipType.ASSIGNED_TO) == []


def test_relationship_index_count_returns_total() -> None:
    relationship_one = EntityRelationship(
        source_type="issue",
        source_id=1,
        target_type="milestone",
        target_id=11,
        relationship_type=RelationshipType.BELONGS_TO_MILESTONE,
        project_id=42,
    )
    relationship_two = EntityRelationship(
        source_type="merge_request",
        source_id=2,
        target_type="pipeline",
        target_id=22,
        relationship_type=RelationshipType.TRIGGERS_PIPELINE,
        project_id=42,
    )
    index = RelationshipIndex(
        by_source={
            ("issue", 1): [relationship_one],
            ("merge_request", 2): [relationship_two],
        }
    )

    assert index.count() == 2


def test_consistency_report_is_healthy_false_only_for_error_issue() -> None:
    warning_issue = ConsistencyIssue(
        severity="WARNING",
        check_name="stale_state",
        entity_type="issue",
        entity_id=1,
        description="warning",
        recommendation="none",
    )
    warning_report = ConsistencyReport(
        project_id=42,
        generated_at=UTC_NOW,
        issues=[warning_issue],
    )
    assert warning_report.is_healthy is True

    error_issue = ConsistencyIssue(
        severity="ERROR",
        check_name="orphaned_reference",
        entity_type="merge_request",
        entity_id=2,
        description="error",
        recommendation="fix reference",
    )
    error_report = ConsistencyReport(
        project_id=42,
        generated_at=UTC_NOW,
        issues=[warning_issue, error_issue],
    )
    assert error_report.is_healthy is False


def test_update_result_reason_uses_canonical_value() -> None:
    result = UpdateResult(
        project_id=42,
        entity_type="issue",
        entity_id=1,
        applied=True,
        reason="applied",
        source=UpdateSource.WEBHOOK,
    )
    assert result.reason == "applied"


def test_project_state_initializes_metadata_project_id() -> None:
    state = ProjectState(project_id=42)
    assert state.metadata.project_id == 42
    assert state.metadata.completeness == StateCompleteness.EMPTY
    assert state.metadata.health == StateHealth.UNKNOWN
