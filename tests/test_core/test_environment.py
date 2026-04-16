"""Tests for environment management."""

from __future__ import annotations

import os

import pytest

from delivery_intelligence.core.environment import (
    get_environment_summary,
    load_environment,
    validate_required_env_vars,
)


def test_load_environment_defaults_to_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DI_ENV", raising=False)
    result = load_environment()
    assert result == "development"


def test_load_environment_reads_di_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DI_ENV", "production")
    result = load_environment()
    assert result == "production"


def test_load_environment_invalid_value_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DI_ENV", "invalid")
    with pytest.raises(ValueError, match="Invalid DI_ENV"):
        load_environment()


def test_validate_development_always_succeeds() -> None:
    validate_required_env_vars("development")  # should not raise


def test_validate_development_succeeds_with_no_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DI_GITLAB__URL", raising=False)
    monkeypatch.delenv("DI_GITLAB__TOKEN", raising=False)
    validate_required_env_vars("development")  # must succeed


def test_validate_production_raises_when_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DI_GITLAB__URL", "https://gitlab.example.com")
    monkeypatch.delenv("DI_GITLAB__TOKEN", raising=False)
    with pytest.raises(EnvironmentError, match="DI_GITLAB__TOKEN"):
        validate_required_env_vars("production")


def test_validate_production_raises_listing_all_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DI_GITLAB__URL", raising=False)
    monkeypatch.delenv("DI_GITLAB__TOKEN", raising=False)
    with pytest.raises(EnvironmentError) as exc_info:
        validate_required_env_vars("production")
    msg = str(exc_info.value)
    assert "DI_GITLAB__URL" in msg
    assert "DI_GITLAB__TOKEN" in msg


def test_validate_staging_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DI_GITLAB__URL", raising=False)
    monkeypatch.delenv("DI_GITLAB__TOKEN", raising=False)
    with pytest.raises(EnvironmentError):
        validate_required_env_vars("staging")


def test_get_environment_summary_returns_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DI_ENV", "development")
    summary = get_environment_summary()
    assert "env" in summary
    assert "python_version" in summary
    assert "platform" in summary
    assert "debug" in summary


def test_get_environment_summary_no_secrets() -> None:
    summary = get_environment_summary()
    token = os.environ.get("DI_GITLAB__TOKEN", "")
    if token:
        assert token not in str(summary)
