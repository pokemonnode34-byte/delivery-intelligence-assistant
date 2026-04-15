"""Tests for environment management utilities (Step 4)."""

import pytest

from delivery_intelligence.core.environment import (
    get_environment_summary,
    load_environment,
    validate_required_env_vars,
)


# ---------------------------------------------------------------------------
# load_environment
# ---------------------------------------------------------------------------


class TestLoadEnvironment:
    def test_defaults_to_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DI_ENV", raising=False)
        assert load_environment() == "development"

    def test_reads_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DI_ENV", "development")
        assert load_environment() == "development"

    def test_reads_staging(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DI_ENV", "staging")
        assert load_environment() == "staging"

    def test_reads_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DI_ENV", "production")
        assert load_environment() == "production"

    def test_invalid_env_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DI_ENV", "invalid")
        with pytest.raises(ValueError, match="Invalid DI_ENV"):
            load_environment()

    def test_empty_env_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DI_ENV", "")
        with pytest.raises(ValueError):
            load_environment()


# ---------------------------------------------------------------------------
# validate_required_env_vars
# ---------------------------------------------------------------------------


class TestValidateRequiredEnvVars:
    def test_development_always_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DI_GITLAB__URL", raising=False)
        monkeypatch.delenv("DI_GITLAB__TOKEN", raising=False)
        validate_required_env_vars("development")  # must not raise

    def test_development_succeeds_even_with_no_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for var in ["DI_GITLAB__URL", "DI_GITLAB__TOKEN", "DI_ENV"]:
            monkeypatch.delenv(var, raising=False)
        validate_required_env_vars("development")  # must not raise

    def test_production_raises_when_all_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DI_GITLAB__URL", raising=False)
        monkeypatch.delenv("DI_GITLAB__TOKEN", raising=False)
        with pytest.raises(EnvironmentError):
            validate_required_env_vars("production")

    def test_production_error_lists_all_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DI_GITLAB__URL", raising=False)
        monkeypatch.delenv("DI_GITLAB__TOKEN", raising=False)
        with pytest.raises(EnvironmentError) as exc_info:
            validate_required_env_vars("production")
        msg = str(exc_info.value)
        assert "DI_GITLAB__URL" in msg
        assert "DI_GITLAB__TOKEN" in msg

    def test_production_succeeds_with_all_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DI_GITLAB__URL", "https://gitlab.example.com")
        monkeypatch.setenv("DI_GITLAB__TOKEN", "token")
        validate_required_env_vars("production")  # must not raise

    def test_staging_raises_when_token_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DI_GITLAB__URL", "https://gitlab.example.com")
        monkeypatch.delenv("DI_GITLAB__TOKEN", raising=False)
        with pytest.raises(EnvironmentError, match="DI_GITLAB__TOKEN"):
            validate_required_env_vars("staging")


# ---------------------------------------------------------------------------
# get_environment_summary
# ---------------------------------------------------------------------------


class TestGetEnvironmentSummary:
    def test_returns_dict(self) -> None:
        summary = get_environment_summary()
        assert isinstance(summary, dict)

    def test_contains_required_keys(self) -> None:
        summary = get_environment_summary()
        for key in ("env", "python_version", "platform", "debug"):
            assert key in summary

    def test_all_values_are_strings(self) -> None:
        summary = get_environment_summary()
        for key, value in summary.items():
            assert isinstance(value, str), (
                f"Key '{key}' has non-string value: {value!r}"
            )

    def test_debug_defaults_to_false_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DI_DEBUG", raising=False)
        summary = get_environment_summary()
        assert summary["debug"] == "false"

    def test_debug_true_when_env_var_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DI_DEBUG", "true")
        summary = get_environment_summary()
        assert summary["debug"] == "true"

    def test_no_secret_values_in_summary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DI_GITLAB__TOKEN", "supersecrettoken")
        summary = get_environment_summary()
        for value in summary.values():
            assert "supersecrettoken" not in value
