"""Webhook payload parsing and validation for GitLab events."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from delivery_intelligence.core.logging import get_logger
from delivery_intelligence.gitlab.mappers import (
    map_issue,
    map_merge_request,
    map_pipeline,
    parse_datetime,
)
from delivery_intelligence.models.base import BaseEntity

_logger = get_logger("gitlab.webhooks")


class WebhookEvent(StrEnum):
    """GitLab webhook event types."""

    PUSH = "PUSH"
    ISSUE = "ISSUE"
    MERGE_REQUEST = "MERGE_REQUEST"
    PIPELINE = "PIPELINE"
    NOTE = "NOTE"
    UNKNOWN = "UNKNOWN"


_HEADER_TO_EVENT: dict[str, WebhookEvent] = {
    "push hook": WebhookEvent.PUSH,
    "issue hook": WebhookEvent.ISSUE,
    "merge request hook": WebhookEvent.MERGE_REQUEST,
    "pipeline hook": WebhookEvent.PIPELINE,
    "note hook": WebhookEvent.NOTE,
    "job hook": WebhookEvent.UNKNOWN,
    "confidential issue hook": WebhookEvent.ISSUE,
    "confidential note hook": WebhookEvent.NOTE,
}


@dataclass
class WebhookPayload:
    """Parsed GitLab webhook payload with ordering metadata.

    Per Invariant 2: received_at is the arrival timestamp (UTC).
    entity_updated_at is the authoritative state timestamp from the payload.
    Downstream consumers must use entity_updated_at, not received_at, for ordering.
    """

    event_type: WebhookEvent
    project_id: int
    object_kind: str
    action: str | None
    raw: dict[str, Any]
    received_at: datetime
    entity_updated_at: datetime | None


def parse_webhook_event(
    headers: dict[str, str], body: dict[str, Any]
) -> WebhookPayload:
    """Parse a GitLab webhook request into a structured WebhookPayload.

    Sets received_at to now(UTC). Extracts entity_updated_at from
    object_attributes.updated_at if present. Unknown event headers
    are mapped to UNKNOWN with a WARNING log.
    """
    event_header = (headers.get("X-Gitlab-Event") or headers.get("x-gitlab-event") or "").lower()
    event_type = _HEADER_TO_EVENT.get(event_header, WebhookEvent.UNKNOWN)

    if event_type == WebhookEvent.UNKNOWN and event_header:
        _logger.warning("unknown_webhook_event_type", event_header=event_header)

    project_id_raw = body.get("project_id") or (body.get("project") or {}).get("id")
    if project_id_raw is None:
        raise ValueError("Webhook payload missing 'project_id'")
    project_id = int(project_id_raw)

    object_kind = str(body.get("object_kind") or "unknown")

    object_attrs = body.get("object_attributes") or {}
    action: str | None = object_attrs.get("action") or body.get("event_name")

    # Per Invariant 2: attach UTC arrival timestamp
    received_at = datetime.now(timezone.utc)

    # Extract authoritative entity state timestamp
    entity_updated_at: datetime | None = None
    updated_str = object_attrs.get("updated_at")
    if updated_str:
        try:
            entity_updated_at = parse_datetime(updated_str)
        except ValueError:
            entity_updated_at = None

    return WebhookPayload(
        event_type=event_type,
        project_id=project_id,
        object_kind=object_kind,
        action=action,
        raw=body,
        received_at=received_at,
        entity_updated_at=entity_updated_at,
    )


def validate_webhook_token(headers: dict[str, str], expected_token: str) -> bool:
    """Validate the GitLab webhook token using constant-time comparison.

    Never logs the token value.
    """
    received = headers.get("X-Gitlab-Token") or headers.get("x-gitlab-token") or ""
    return hmac.compare_digest(received, expected_token)


def map_webhook_to_model(payload: WebhookPayload) -> BaseEntity | None:
    """Map a parsed webhook payload to a domain model.

    Returns None for PUSH, NOTE, and UNKNOWN events — this is intentional,
    not an error. These event types have no domain model mapping.

    Raises ValueError if the payload is for a mapped event type but the
    data is malformed.
    """
    if payload.event_type in (WebhookEvent.PUSH, WebhookEvent.NOTE, WebhookEvent.UNKNOWN):
        return None

    object_attrs = payload.raw.get("object_attributes") or {}

    try:
        if payload.event_type == WebhookEvent.ISSUE:
            return map_issue(object_attrs)
        if payload.event_type == WebhookEvent.MERGE_REQUEST:
            return map_merge_request(object_attrs)
        if payload.event_type == WebhookEvent.PIPELINE:
            return map_pipeline(object_attrs)
    except (KeyError, ValueError, Exception) as e:
        _logger.error(
            "webhook_mapping_failed",
            event_type=payload.event_type.value,
            project_id=payload.project_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise ValueError(
            f"Failed to map {payload.event_type.value} webhook: {e}"
        ) from e

    return None
