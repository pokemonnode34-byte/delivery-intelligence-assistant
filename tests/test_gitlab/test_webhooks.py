"""Tests for webhook payload parsing and model mapping."""

from __future__ import annotations

import json
from datetime import timezone
from pathlib import Path

import pytest

from delivery_intelligence.gitlab.webhooks import (
    WebhookEvent,
    map_webhook_to_model,
    parse_webhook_event,
    validate_webhook_token,
)
from delivery_intelligence.models.issue import Issue
from delivery_intelligence.models.merge_request import MergeRequest
from delivery_intelligence.models.pipeline import Pipeline

FIXTURES = Path(__file__).parent.parent / "fixtures" / "gitlab"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_parse_push_webhook() -> None:
    body = load_fixture("webhook_push.json")
    headers = {"X-Gitlab-Event": "Push Hook"}
    payload = parse_webhook_event(headers, body)
    assert payload.event_type == WebhookEvent.PUSH
    assert payload.project_id == 1
    assert payload.received_at.tzinfo == timezone.utc


def test_parse_issue_webhook() -> None:
    body = load_fixture("webhook_issue.json")
    headers = {"X-Gitlab-Event": "Issue Hook"}
    payload = parse_webhook_event(headers, body)
    assert payload.event_type == WebhookEvent.ISSUE
    assert payload.entity_updated_at is not None


def test_parse_merge_request_webhook() -> None:
    body = load_fixture("webhook_merge_request.json")
    headers = {"X-Gitlab-Event": "Merge Request Hook"}
    payload = parse_webhook_event(headers, body)
    assert payload.event_type == WebhookEvent.MERGE_REQUEST


def test_parse_pipeline_webhook() -> None:
    body = load_fixture("webhook_pipeline.json")
    headers = {"X-Gitlab-Event": "Pipeline Hook"}
    payload = parse_webhook_event(headers, body)
    assert payload.event_type == WebhookEvent.PIPELINE


def test_parse_unknown_event_returns_unknown() -> None:
    body = {"object_kind": "custom", "project_id": 1}
    headers = {"X-Gitlab-Event": "Custom Hook"}
    payload = parse_webhook_event(headers, body)
    assert payload.event_type == WebhookEvent.UNKNOWN


def test_parse_missing_project_id_raises() -> None:
    body = {"object_kind": "push"}
    headers = {"X-Gitlab-Event": "Push Hook"}
    with pytest.raises(ValueError, match="project_id"):
        parse_webhook_event(headers, body)


def test_received_at_is_utc() -> None:
    body = load_fixture("webhook_push.json")
    headers = {"X-Gitlab-Event": "Push Hook"}
    payload = parse_webhook_event(headers, body)
    assert payload.received_at.tzinfo is not None
    assert payload.received_at.tzinfo == timezone.utc


def test_validate_webhook_token_correct() -> None:
    headers = {"X-Gitlab-Token": "secret"}
    assert validate_webhook_token(headers, "secret") is True


def test_validate_webhook_token_wrong() -> None:
    headers = {"X-Gitlab-Token": "wrong"}
    assert validate_webhook_token(headers, "secret") is False


def test_validate_webhook_token_missing() -> None:
    assert validate_webhook_token({}, "secret") is False


def test_map_issue_webhook_to_model() -> None:
    body = load_fixture("webhook_issue.json")
    headers = {"X-Gitlab-Event": "Issue Hook"}
    payload = parse_webhook_event(headers, body)
    model = map_webhook_to_model(payload)
    assert isinstance(model, Issue)


def test_map_merge_request_webhook_to_model() -> None:
    body = load_fixture("webhook_merge_request.json")
    headers = {"X-Gitlab-Event": "Merge Request Hook"}
    payload = parse_webhook_event(headers, body)
    model = map_webhook_to_model(payload)
    assert isinstance(model, MergeRequest)


def test_map_pipeline_webhook_to_model() -> None:
    body = load_fixture("webhook_pipeline.json")
    headers = {"X-Gitlab-Event": "Pipeline Hook"}
    payload = parse_webhook_event(headers, body)
    model = map_webhook_to_model(payload)
    assert isinstance(model, Pipeline)


def test_map_push_webhook_returns_none() -> None:
    body = load_fixture("webhook_push.json")
    headers = {"X-Gitlab-Event": "Push Hook"}
    payload = parse_webhook_event(headers, body)
    assert map_webhook_to_model(payload) is None


def test_map_unknown_webhook_returns_none() -> None:
    body = {"object_kind": "custom", "project_id": 1}
    headers = {"X-Gitlab-Event": "Custom Hook"}
    payload = parse_webhook_event(headers, body)
    assert map_webhook_to_model(payload) is None
