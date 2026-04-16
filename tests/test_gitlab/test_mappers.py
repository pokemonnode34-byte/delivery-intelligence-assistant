"""Tests for response mappers."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import timezone

import pytest

from delivery_intelligence.gitlab.mappers import (
    map_contributor,
    map_issue,
    map_merge_request,
    map_milestone,
    map_pipeline,
    map_project,
    parse_date,
    parse_datetime,
)
from delivery_intelligence.models.base import EntityStatus, Priority
from delivery_intelligence.models.pipeline import PipelineStatus
from delivery_intelligence.models.milestone import MilestoneState

FIXTURES = Path(__file__).parent.parent / "fixtures" / "gitlab"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_map_project_from_fixture() -> None:
    raw = load_fixture("project.json")
    p = map_project(raw)
    assert p.id == 1
    assert p.name == "my-project"
    assert p.path_with_namespace == "group/my-project"
    assert p.visibility == "private"
    assert p.created_at.tzinfo is not None
    assert p.created_at.tzinfo == timezone.utc


def test_map_issue_from_fixture() -> None:
    raw = load_fixture("issue.json")
    issue = map_issue(raw)
    assert issue.id == 100
    assert issue.iid == 1
    assert issue.project_id == 1
    assert issue.state == EntityStatus.OPEN
    assert issue.priority == Priority.HIGH
    assert "backend" in issue.labels
    assert issue.assignee_ids == [43]
    assert issue.author_id == 42
    assert issue.milestone_id == 5
    assert issue.blocking_issues_count == 2
    assert issue.time_estimate == 3600
    assert issue.time_spent == 1800


def test_map_issue_unknown_state_defaults_to_open() -> None:
    raw = load_fixture("issue.json")
    raw = {**raw, "state": "unknown_state"}
    issue = map_issue(raw)
    assert issue.state == EntityStatus.OPEN


def test_map_merge_request_from_fixture() -> None:
    raw = load_fixture("merge_request.json")
    mr = map_merge_request(raw)
    assert mr.id == 200
    assert mr.state == EntityStatus.OPEN
    assert mr.changes_count == 12
    assert mr.pipeline_id == 500
    assert mr.reviewer_ids == [44]


def test_map_merge_request_merged_state() -> None:
    raw = load_fixture("merge_request.json")
    raw = {**raw, "state": "merged", "merged_at": "2024-01-16T00:00:00Z"}
    mr = map_merge_request(raw)
    assert mr.state == EntityStatus.MERGED


def test_map_pipeline_from_fixture() -> None:
    raw = load_fixture("pipeline.json")
    p = map_pipeline(raw)
    assert p.id == 500
    assert p.status == PipelineStatus.SUCCESS
    assert p.duration == 120
    assert p.started_at is not None


def test_map_pipeline_unknown_status_defaults_to_created() -> None:
    raw = load_fixture("pipeline.json")
    raw = {**raw, "status": "totally_unknown"}
    p = map_pipeline(raw)
    assert p.status == PipelineStatus.CREATED


def test_map_milestone_from_fixture() -> None:
    raw = load_fixture("milestone.json")
    m = map_milestone(raw)
    assert m.id == 5
    assert m.state == MilestoneState.ACTIVE
    assert str(m.due_date) == "2024-03-01"


def test_map_contributor_from_fixture() -> None:
    raw = load_fixture("contributor.json")
    c = map_contributor(raw)
    assert c.id == 42
    assert c.username == "alice"
    assert c.is_active is True


def test_map_issue_missing_optional_fields() -> None:
    minimal = {
        "id": 1, "iid": 1, "project_id": 1, "title": "t",
        "state": "opened",
        "author": {"id": 1},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    issue = map_issue(minimal)
    assert issue.description is None
    assert issue.milestone_id is None
    assert issue.due_date is None
    assert issue.closed_at is None
    assert issue.labels == []
    assert issue.assignee_ids == []


def test_map_issue_invalid_raises_value_error() -> None:
    with pytest.raises(ValueError):
        map_issue({"id": 1, "title": "x"})  # missing required fields


def test_parse_datetime_z_suffix() -> None:
    dt = parse_datetime("2024-01-15T10:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_datetime_none_returns_none() -> None:
    assert parse_datetime(None) is None


def test_parse_datetime_invalid_raises() -> None:
    with pytest.raises(ValueError):
        parse_datetime("not-a-date")


def test_parse_date_none_returns_none() -> None:
    assert parse_date(None) is None


def test_priority_extraction_from_labels() -> None:
    raw = load_fixture("issue.json")
    raw = {**raw, "labels": ["priority::critical", "other"]}
    issue = map_issue(raw)
    assert issue.priority == Priority.CRITICAL
