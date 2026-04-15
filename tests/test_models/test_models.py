"""Tests for domain models (Step 6)."""

from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from delivery_intelligence.models import (
    BaseEntity,
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
    RiskLevel,
    UTCDatetime,
)

UTC_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# UTCDatetime validator
# ---------------------------------------------------------------------------


class TestUTCDatetime:
    """Test the UTCDatetime annotated type directly through a helper model."""

    from pydantic import BaseModel as _BaseModel

    class _M(_BaseModel):
        dt: UTCDatetime

    def test_accepts_utc_datetime(self) -> None:
        m = self._M(dt=UTC_NOW)
        assert m.dt.tzinfo == timezone.utc

    def test_rejects_naive_datetime(self) -> None:
        with pytest.raises(ValidationError):
            self._M(dt=datetime(2024, 1, 1, 12, 0, 0))

    def test_normalizes_aware_non_utc_to_utc(self) -> None:
        tz_plus5 = timezone(timedelta(hours=5))
        aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=tz_plus5)
        m = self._M(dt=aware)
        assert m.dt.tzinfo == timezone.utc
        assert m.dt.hour == 7  # 12:00+05:00 → 07:00 UTC

    def test_accepts_utc_aware_string(self) -> None:
        m = self._M(dt="2024-01-15T10:30:00+00:00")
        assert m.dt.tzinfo == timezone.utc

    def test_rejects_naive_string(self) -> None:
        with pytest.raises(ValidationError):
            self._M(dt="2024-01-15T10:30:00")

    def test_utc_datetime_passthrough(self) -> None:
        utc_dt = datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        m = self._M(dt=utc_dt)
        assert m.dt == utc_dt


# ---------------------------------------------------------------------------
# BaseEntity config
# ---------------------------------------------------------------------------


class TestBaseEntity:
    def test_is_frozen(self) -> None:
        contributor = Contributor(id=1, username="user", name="User Name")
        with pytest.raises(Exception):
            contributor.username = "other"  # type: ignore[misc]

    def test_model_copy_creates_new_instance(self) -> None:
        c = Contributor(id=1, username="jdoe", name="John Doe")
        c2 = c.model_copy(update={"username": "jsmith"})
        assert c2.username == "jsmith"
        assert c.username == "jdoe"  # original unchanged


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class TestProject:
    def test_valid_construction(self) -> None:
        p = Project(
            id=1,
            name="my-project",
            path_with_namespace="group/my-project",
            web_url="https://gitlab.example.com/group/my-project",
            visibility="private",
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
        )
        assert p.id == 1
        assert p.default_branch == "main"
        assert p.description is None
        assert p.last_activity_at is None

    def test_naive_datetime_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Project(
                id=1,
                name="p",
                path_with_namespace="g/p",
                web_url="https://gitlab.example.com/g/p",
                visibility="private",
                created_at=datetime(2024, 1, 1),  # naive
                updated_at=UTC_NOW,
            )

    def test_non_utc_normalized(self) -> None:
        tz_plus2 = timezone(timedelta(hours=2))
        aware = datetime(2024, 3, 1, 14, 0, 0, tzinfo=tz_plus2)
        p = Project(
            id=1,
            name="p",
            path_with_namespace="g/p",
            web_url="https://gitlab.example.com/g/p",
            visibility="private",
            created_at=aware,
            updated_at=UTC_NOW,
        )
        assert p.created_at.tzinfo == timezone.utc
        assert p.created_at.hour == 12  # 14:00+02:00 → 12:00 UTC

    def test_model_dump_serializes_timezone_aware(self) -> None:
        p = Project(
            id=1,
            name="p",
            path_with_namespace="g/p",
            web_url="https://gitlab.example.com/g/p",
            visibility="private",
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
        )
        dumped = p.model_dump()
        assert isinstance(dumped["created_at"], datetime)
        assert dumped["created_at"].tzinfo is not None


# ---------------------------------------------------------------------------
# Issue
# ---------------------------------------------------------------------------


class TestIssue:
    def _make_issue(self, **kwargs: object) -> Issue:
        defaults: dict[str, object] = dict(
            id=100,
            iid=1,
            project_id=10,
            title="Fix bug",
            state=EntityStatus.OPEN,
            author_id=5,
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
        )
        defaults.update(kwargs)
        return Issue(**defaults)  # type: ignore[arg-type]

    def test_valid_construction(self) -> None:
        issue = self._make_issue()
        assert issue.id == 100
        assert issue.priority == Priority.NONE
        assert issue.labels == []
        assert issue.assignee_ids == []
        assert issue.blocking_issues_count == 0

    def test_list_defaults_are_empty(self) -> None:
        issue = self._make_issue()
        assert issue.labels == []
        assert issue.assignee_ids == []

    def test_list_defaults_not_shared_across_instances(self) -> None:
        a = self._make_issue(id=1, iid=1)
        b = self._make_issue(id=2, iid=2)
        assert a.labels is not b.labels
        assert a.assignee_ids is not b.assignee_ids

    def test_due_date_is_plain_date(self) -> None:
        issue = self._make_issue(due_date=date(2024, 12, 31))
        assert issue.due_date == date(2024, 12, 31)

    def test_optional_fields_default_none(self) -> None:
        issue = self._make_issue()
        assert issue.closed_at is None
        assert issue.milestone_id is None
        assert issue.weight is None


# ---------------------------------------------------------------------------
# MergeRequest
# ---------------------------------------------------------------------------


class TestMergeRequest:
    def _make_mr(self, **kwargs: object) -> MergeRequest:
        defaults: dict[str, object] = dict(
            id=200,
            iid=5,
            project_id=10,
            title="Add feature",
            state=EntityStatus.OPEN,
            source_branch="feature/x",
            target_branch="main",
            author_id=5,
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
        )
        defaults.update(kwargs)
        return MergeRequest(**defaults)  # type: ignore[arg-type]

    def test_valid_construction(self) -> None:
        mr = self._make_mr()
        assert mr.has_conflicts is False
        assert mr.draft is False
        assert mr.assignee_ids == []
        assert mr.reviewer_ids == []
        assert mr.labels == []

    def test_list_defaults_not_shared(self) -> None:
        a = self._make_mr(id=1, iid=1)
        b = self._make_mr(id=2, iid=2)
        assert a.labels is not b.labels


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class TestPipeline:
    def _make_pipeline(self, **kwargs: object) -> Pipeline:
        defaults: dict[str, object] = dict(
            id=300,
            project_id=10,
            ref="main",
            sha="abc123",
            status=PipelineStatus.SUCCESS,
            source="push",
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
        )
        defaults.update(kwargs)
        return Pipeline(**defaults)  # type: ignore[arg-type]

    def test_valid_construction(self) -> None:
        p = self._make_pipeline()
        assert p.status == PipelineStatus.SUCCESS
        assert p.duration is None

    def test_pipeline_status_string_values(self) -> None:
        assert PipelineStatus.RUNNING == "RUNNING"
        assert PipelineStatus.FAILED == "FAILED"
        assert PipelineStatus.CANCELED == "CANCELED"


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------


class TestMilestone:
    def _make_milestone(self, **kwargs: object) -> Milestone:
        defaults: dict[str, object] = dict(
            id=400,
            iid=1,
            project_id=10,
            title="v1.0",
            state=MilestoneState.ACTIVE,
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
        )
        defaults.update(kwargs)
        return Milestone(**defaults)  # type: ignore[arg-type]

    def test_valid_construction(self) -> None:
        m = self._make_milestone()
        assert m.expired is False
        assert m.state == MilestoneState.ACTIVE

    def test_optional_dates_default_none(self) -> None:
        m = self._make_milestone()
        assert m.due_date is None
        assert m.start_date is None


# ---------------------------------------------------------------------------
# Contributor
# ---------------------------------------------------------------------------


class TestContributor:
    def test_valid_construction(self) -> None:
        c = Contributor(id=1, username="jdoe", name="John Doe")
        assert c.is_active is True
        assert c.email is None

    def test_extends_base_entity(self) -> None:
        c = Contributor(id=1, username="jdoe", name="John Doe")
        assert isinstance(c, BaseEntity)

    def test_optional_fields_default_none(self) -> None:
        c = Contributor(id=1, username="u", name="N")
        assert c.avatar_url is None
        assert c.web_url is None


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TestEntityStatus:
    def test_string_values(self) -> None:
        assert EntityStatus.OPEN == "OPEN"
        assert EntityStatus.CLOSED == "CLOSED"
        assert EntityStatus.MERGED == "MERGED"
        assert EntityStatus.IN_PROGRESS == "IN_PROGRESS"
        assert EntityStatus.BLOCKED == "BLOCKED"


class TestPriority:
    def test_string_values(self) -> None:
        assert Priority.CRITICAL == "CRITICAL"
        assert Priority.HIGH == "HIGH"
        assert Priority.NONE == "NONE"


class TestRiskLevel:
    def test_string_values(self) -> None:
        assert RiskLevel.CRITICAL == "CRITICAL"
        assert RiskLevel.LOW == "LOW"
        assert RiskLevel.NONE == "NONE"


class TestMilestoneState:
    def test_string_values(self) -> None:
        assert MilestoneState.ACTIVE == "ACTIVE"
        assert MilestoneState.CLOSED == "CLOSED"


class TestPipelineStatus:
    def test_all_values_present(self) -> None:
        expected = {
            "CREATED", "WAITING_FOR_RESOURCE", "PREPARING", "PENDING",
            "RUNNING", "SUCCESS", "FAILED", "CANCELED", "SKIPPED",
            "MANUAL", "SCHEDULED",
        }
        actual = {s.value for s in PipelineStatus}
        assert actual == expected
