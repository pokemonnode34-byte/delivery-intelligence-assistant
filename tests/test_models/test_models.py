"""Tests for domain models."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from delivery_intelligence.models import (
    Contributor,
    EntityStatus,
    Issue,
    MergeRequest,
    Milestone,
    MilestoneState,
    Pipeline,
    PipelineStatus,
    Priority,
    Project,
)

UTC = timezone.utc
NOW_UTC = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)


def test_project_instantiation() -> None:
    p = Project(
        id=1,
        name="my-project",
        path_with_namespace="group/my-project",
        web_url="https://gitlab.example.com/group/my-project",
        visibility="private",
        created_at=NOW_UTC,
        updated_at=NOW_UTC,
    )
    assert p.id == 1
    assert p.name == "my-project"
    assert p.default_branch == "main"


def test_project_rejects_naive_datetime() -> None:
    naive = datetime(2024, 1, 15, 10, 0, 0)
    with pytest.raises(ValidationError):
        Project(
            id=1,
            name="x",
            path_with_namespace="g/x",
            web_url="https://example.com",
            visibility="private",
            created_at=naive,
            updated_at=NOW_UTC,
        )


def test_project_normalizes_non_utc_datetime() -> None:
    tz_plus5 = timezone(timedelta(hours=5))
    dt_plus5 = datetime(2024, 1, 15, 15, 0, 0, tzinfo=tz_plus5)
    p = Project(
        id=1,
        name="x",
        path_with_namespace="g/x",
        web_url="https://example.com",
        visibility="private",
        created_at=dt_plus5,
        updated_at=NOW_UTC,
    )
    assert p.created_at.tzinfo == UTC
    assert p.created_at == datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)


def test_issue_instantiation() -> None:
    issue = Issue(
        id=100,
        iid=1,
        project_id=1,
        title="Fix bug",
        state=EntityStatus.OPEN,
        author_id=42,
        created_at=NOW_UTC,
        updated_at=NOW_UTC,
    )
    assert issue.id == 100
    assert issue.priority == Priority.NONE
    assert issue.labels == []
    assert issue.assignee_ids == []
    assert issue.blocking_issues_count == 0


def test_issue_labels_use_factory() -> None:
    i1 = Issue(id=1, iid=1, project_id=1, title="t", state=EntityStatus.OPEN,
               author_id=1, created_at=NOW_UTC, updated_at=NOW_UTC)
    i2 = Issue(id=2, iid=2, project_id=1, title="t", state=EntityStatus.OPEN,
               author_id=1, created_at=NOW_UTC, updated_at=NOW_UTC)
    assert i1.labels is not i2.labels


def test_merge_request_instantiation() -> None:
    mr = MergeRequest(
        id=10,
        iid=1,
        project_id=1,
        title="Add feature",
        state=EntityStatus.OPEN,
        source_branch="feature",
        target_branch="main",
        author_id=1,
        created_at=NOW_UTC,
        updated_at=NOW_UTC,
    )
    assert mr.has_conflicts is False
    assert mr.draft is False


def test_pipeline_instantiation() -> None:
    p = Pipeline(
        id=500,
        project_id=1,
        ref="main",
        sha="abc123",
        status=PipelineStatus.SUCCESS,
        source="push",
        created_at=NOW_UTC,
        updated_at=NOW_UTC,
    )
    assert p.status == PipelineStatus.SUCCESS


def test_milestone_instantiation() -> None:
    m = Milestone(
        id=5,
        iid=1,
        project_id=1,
        title="v1.0",
        state=MilestoneState.ACTIVE,
        created_at=NOW_UTC,
        updated_at=NOW_UTC,
    )
    assert m.expired is False


def test_contributor_no_datetimes() -> None:
    c = Contributor(id=1, username="alice", name="Alice Smith")
    assert c.is_active is True
    assert c.email is None


def test_frozen_model_rejects_mutation() -> None:
    p = Project(
        id=1, name="x", path_with_namespace="g/x",
        web_url="https://example.com", visibility="private",
        created_at=NOW_UTC, updated_at=NOW_UTC,
    )
    with pytest.raises(Exception):
        p.name = "new_name"  # type: ignore[misc]


def test_model_copy_with_update() -> None:
    p = Project(
        id=1, name="original", path_with_namespace="g/x",
        web_url="https://example.com", visibility="private",
        created_at=NOW_UTC, updated_at=NOW_UTC,
    )
    p2 = p.model_copy(update={"name": "updated"})
    assert p2.name == "updated"
    assert p.name == "original"


def test_model_dump_preserves_utc_datetimes() -> None:
    p = Project(
        id=1, name="x", path_with_namespace="g/x",
        web_url="https://example.com", visibility="private",
        created_at=NOW_UTC, updated_at=NOW_UTC,
    )
    dumped = p.model_dump()
    assert dumped["created_at"].tzinfo is not None


def test_utcdatetime_parses_z_suffix() -> None:
    issue = Issue(
        id=1, iid=1, project_id=1, title="t", state=EntityStatus.OPEN,
        author_id=1,
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
    )
    assert issue.created_at.tzinfo is not None
