"""Response mappers: transform raw GitLab JSON into Phase 0 domain models."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from delivery_intelligence.models.base import EntityStatus, Priority
from delivery_intelligence.models.contributor import Contributor
from delivery_intelligence.models.issue import Issue
from delivery_intelligence.models.merge_request import MergeRequest
from delivery_intelligence.models.milestone import Milestone, MilestoneState
from delivery_intelligence.models.pipeline import Pipeline, PipelineStatus
from delivery_intelligence.models.project import Project

_logger = logging.getLogger(__name__)

_ISSUE_STATE_MAP: dict[str, EntityStatus] = {
    "opened": EntityStatus.OPEN,
    "closed": EntityStatus.CLOSED,
}

_MR_STATE_MAP: dict[str, EntityStatus] = {
    "opened": EntityStatus.OPEN,
    "closed": EntityStatus.CLOSED,
    "merged": EntityStatus.MERGED,
    "locked": EntityStatus.LOCKED,
}

_MILESTONE_STATE_MAP: dict[str, MilestoneState] = {
    "active": MilestoneState.ACTIVE,
    "closed": MilestoneState.CLOSED,
}

_PIPELINE_STATUS_MAP: dict[str, PipelineStatus] = {
    "created": PipelineStatus.CREATED,
    "waiting_for_resource": PipelineStatus.WAITING_FOR_RESOURCE,
    "preparing": PipelineStatus.PREPARING,
    "pending": PipelineStatus.PENDING,
    "running": PipelineStatus.RUNNING,
    "success": PipelineStatus.SUCCESS,
    "failed": PipelineStatus.FAILED,
    "canceled": PipelineStatus.CANCELED,
    "cancelled": PipelineStatus.CANCELED,
    "skipped": PipelineStatus.SKIPPED,
    "manual": PipelineStatus.MANUAL,
    "scheduled": PipelineStatus.SCHEDULED,
}


def parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 string to UTC-aware datetime.

    Returns None only when value is None.
    Raises ValueError for non-None unparseable values.
    """
    if value is None:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            raise ValueError(f"Naive datetime not allowed: {value!r}")
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot parse datetime from value: {value!r}") from e


def parse_date(value: str | None) -> date | None:
    """Parse ISO 8601 date string to date object.

    Returns None when value is None or empty.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot parse date from value: {value!r}") from e


def _extract_assignee_ids(raw: dict[str, Any]) -> list[int]:
    assignees = raw.get("assignees")
    if not assignees:
        return []
    if not isinstance(assignees, list):
        return []
    return [int(a["id"]) for a in assignees if isinstance(a, dict) and "id" in a]


def _extract_reviewer_ids(raw: dict[str, Any]) -> list[int]:
    reviewers = raw.get("reviewers")
    if not reviewers:
        return []
    if not isinstance(reviewers, list):
        return []
    return [int(r["id"]) for r in reviewers if isinstance(r, dict) and "id" in r]


def _extract_author_id(raw: dict[str, Any]) -> int:
    author = raw.get("author")
    if author is None or not isinstance(author, dict):
        raise ValueError("Issue/MR response missing 'author' object")
    author_id = author.get("id")
    if author_id is None:
        raise ValueError("'author' object missing 'id' field")
    return int(author_id)


def _extract_nested_id(raw: dict[str, Any], key: str) -> int | None:
    obj = raw.get(key)
    if obj is None or not isinstance(obj, dict):
        return None
    obj_id = obj.get("id")
    if obj_id is None:
        return None
    return int(obj_id)


def _extract_priority_from_labels(labels: list[str]) -> Priority:
    for label in labels:
        lower = label.lower()
        if lower.startswith("priority::"):
            value = lower.split("::", 1)[1].strip()
            for p in Priority:
                if p.value.lower() == value:
                    return p
    return Priority.NONE


def map_project(raw: dict[str, Any]) -> Project:
    """Map a raw GitLab project JSON response to a Project domain model."""
    try:
        return Project(
            id=int(raw["id"]),
            name=str(raw["name"]),
            path_with_namespace=str(raw["path_with_namespace"]),
            description=raw.get("description"),
            web_url=str(raw["web_url"]),
            default_branch=raw.get("default_branch") or "main",
            visibility=str(raw["visibility"]),
            created_at=parse_datetime(raw["created_at"]),  # type: ignore[arg-type]
            updated_at=parse_datetime(raw["updated_at"]),  # type: ignore[arg-type]
            last_activity_at=parse_datetime(raw.get("last_activity_at")),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Failed to map project (id={raw.get('id', 'unknown')}): {e}") from e


def map_issue(raw: dict[str, Any]) -> Issue:
    """Map a raw GitLab issue JSON response to an Issue domain model."""
    try:
        labels: list[str] = raw.get("labels") or []
        priority = _extract_priority_from_labels(labels)

        raw_state = raw.get("state", "opened")
        state = _ISSUE_STATE_MAP.get(str(raw_state).lower(), EntityStatus.OPEN)
        if str(raw_state).lower() not in _ISSUE_STATE_MAP:
            _logger.warning("Unknown issue state '%s', defaulting to OPEN", raw_state)

        raw_blocking = raw.get("blocking_issues_count")
        blocking = int(raw_blocking) if raw_blocking is not None else 0

        return Issue(
            id=int(raw["id"]),
            iid=int(raw["iid"]),
            project_id=int(raw["project_id"]),
            title=str(raw["title"]),
            description=raw.get("description"),
            state=state,
            priority=priority,
            labels=labels,
            assignee_ids=_extract_assignee_ids(raw),
            author_id=_extract_author_id(raw),
            milestone_id=_extract_nested_id(raw, "milestone"),
            due_date=parse_date(raw.get("due_date")),
            weight=raw.get("weight"),
            time_estimate=raw.get("time_stats", {}).get("time_estimate") if isinstance(raw.get("time_stats"), dict) else None,
            time_spent=raw.get("time_stats", {}).get("total_time_spent") if isinstance(raw.get("time_stats"), dict) else None,
            blocking_issues_count=blocking,
            created_at=parse_datetime(raw["created_at"]),  # type: ignore[arg-type]
            updated_at=parse_datetime(raw["updated_at"]),  # type: ignore[arg-type]
            closed_at=parse_datetime(raw.get("closed_at")),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Failed to map issue (id={raw.get('id', 'unknown')}): {e}") from e


def map_merge_request(raw: dict[str, Any]) -> MergeRequest:
    """Map a raw GitLab MR JSON response to a MergeRequest domain model."""
    try:
        raw_state = raw.get("state", "opened")
        state = _MR_STATE_MAP.get(str(raw_state).lower(), EntityStatus.OPEN)
        if str(raw_state).lower() not in _MR_STATE_MAP:
            _logger.warning("Unknown MR state '%s', defaulting to OPEN", raw_state)

        changes_count_raw = raw.get("changes_count")
        changes_count: int | None = None
        if changes_count_raw is not None:
            try:
                changes_count = int(changes_count_raw)
            except (ValueError, TypeError):
                changes_count = None

        return MergeRequest(
            id=int(raw["id"]),
            iid=int(raw["iid"]),
            project_id=int(raw["project_id"]),
            title=str(raw["title"]),
            description=raw.get("description"),
            state=state,
            source_branch=str(raw["source_branch"]),
            target_branch=str(raw["target_branch"]),
            author_id=_extract_author_id(raw),
            assignee_ids=_extract_assignee_ids(raw),
            reviewer_ids=_extract_reviewer_ids(raw),
            labels=raw.get("labels") or [],
            milestone_id=_extract_nested_id(raw, "milestone"),
            pipeline_id=_extract_nested_id(raw, "pipeline"),
            has_conflicts=bool(raw.get("has_conflicts", False)),
            draft=bool(raw.get("draft", False)),
            changes_count=changes_count,
            created_at=parse_datetime(raw["created_at"]),  # type: ignore[arg-type]
            updated_at=parse_datetime(raw["updated_at"]),  # type: ignore[arg-type]
            merged_at=parse_datetime(raw.get("merged_at")),
            closed_at=parse_datetime(raw.get("closed_at")),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Failed to map merge_request (id={raw.get('id', 'unknown')}): {e}") from e


def map_pipeline(raw: dict[str, Any]) -> Pipeline:
    """Map a raw GitLab pipeline JSON response to a Pipeline domain model."""
    try:
        raw_status = raw.get("status", "created")
        status = _PIPELINE_STATUS_MAP.get(str(raw_status).lower(), PipelineStatus.CREATED)
        if str(raw_status).lower() not in _PIPELINE_STATUS_MAP:
            _logger.warning("Unknown pipeline status '%s', defaulting to CREATED", raw_status)

        return Pipeline(
            id=int(raw["id"]),
            project_id=int(raw["project_id"]),
            ref=str(raw["ref"]),
            sha=str(raw["sha"]),
            status=status,
            source=str(raw.get("source") or "unknown"),
            duration=raw.get("duration"),
            queued_duration=raw.get("queued_duration"),
            started_at=parse_datetime(raw.get("started_at")),
            finished_at=parse_datetime(raw.get("finished_at")),
            created_at=parse_datetime(raw["created_at"]),  # type: ignore[arg-type]
            updated_at=parse_datetime(raw["updated_at"]),  # type: ignore[arg-type]
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Failed to map pipeline (id={raw.get('id', 'unknown')}): {e}") from e


def map_milestone(raw: dict[str, Any]) -> Milestone:
    """Map a raw GitLab milestone JSON response to a Milestone domain model."""
    try:
        raw_state = raw.get("state", "active")
        state = _MILESTONE_STATE_MAP.get(str(raw_state).lower(), MilestoneState.ACTIVE)
        if str(raw_state).lower() not in _MILESTONE_STATE_MAP:
            _logger.warning("Unknown milestone state '%s', defaulting to ACTIVE", raw_state)

        return Milestone(
            id=int(raw["id"]),
            iid=int(raw["iid"]),
            project_id=int(raw["project_id"]),
            title=str(raw["title"]),
            description=raw.get("description"),
            state=state,
            due_date=parse_date(raw.get("due_date")),
            start_date=parse_date(raw.get("start_date")),
            expired=bool(raw.get("expired", False)),
            created_at=parse_datetime(raw["created_at"]),  # type: ignore[arg-type]
            updated_at=parse_datetime(raw["updated_at"]),  # type: ignore[arg-type]
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Failed to map milestone (id={raw.get('id', 'unknown')}): {e}") from e


def map_contributor(raw: dict[str, Any]) -> Contributor:
    """Map a raw GitLab member/contributor JSON response to a Contributor domain model."""
    try:
        state_val = raw.get("state", "active")
        is_active = str(state_val).lower() == "active"

        return Contributor(
            id=int(raw["id"]),
            username=str(raw["username"]),
            name=str(raw["name"]),
            email=raw.get("email"),
            avatar_url=raw.get("avatar_url"),
            web_url=raw.get("web_url"),
            is_active=is_active,
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Failed to map contributor (id={raw.get('id', 'unknown')}): {e}") from e
