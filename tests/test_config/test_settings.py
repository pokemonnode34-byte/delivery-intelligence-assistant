"""Tests for configuration settings models."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from delivery_intelligence.config.loader import load_settings, load_yaml, merge_configs
from delivery_intelligence.config.settings import (
    AppSettings,
    GitLabSettings,
    LoggingSettings,
)


def test_app_settings_loads_with_defaults() -> None:
    settings = AppSettings()
    assert settings.env == "development"
    assert settings.app_name == "delivery-intelligence"
    assert settings.version == "0.1.0"
    assert settings.debug is False


def test_app_settings_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DI_GITLAB__URL", "https://custom.gitlab.com")
    settings = AppSettings()
    assert settings.gitlab.url == "https://custom.gitlab.com"


def test_app_settings_logging_level_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DI_LOGGING__LEVEL", "DEBUG")
    settings = AppSettings()
    assert settings.logging.level == "DEBUG"


def test_app_settings_invalid_logging_level_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DI_LOGGING__LEVEL", "INVALID")
    with pytest.raises(ValidationError):
        AppSettings()


def test_gitlab_token_not_in_repr() -> None:
    settings = GitLabSettings(url="https://gitlab.example.com", token=SecretStr("my-secret-token"))
    assert "my-secret-token" not in repr(settings)
    assert "my-secret-token" not in str(settings)


def test_gitlab_url_strips_trailing_slash() -> None:
    settings = GitLabSettings(url="https://gitlab.example.com/", token=SecretStr("t"))
    assert settings.url == "https://gitlab.example.com"


def test_gitlab_per_page_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        GitLabSettings(url="https://gitlab.example.com", token=SecretStr("t"), per_page=200)


def test_gitlab_timeout_zero_raises() -> None:
    with pytest.raises(ValidationError):
        GitLabSettings(url="https://gitlab.example.com", token=SecretStr("t"), timeout=0)


def test_logging_file_output_requires_file_path() -> None:
    with pytest.raises(ValidationError):
        LoggingSettings(output="file", file_path=None)


def test_app_settings_model_dump_does_not_expose_token() -> None:
    settings = AppSettings()
    dumped = settings.model_dump()
    gitlab = dumped["gitlab"]
    token_val = gitlab["token"]
    # SecretStr serializes as a dict with get_secret_value not exposed
    assert "not-set" not in str(token_val)


# --- Loader tests ---


def test_load_settings_development_defaults() -> None:
    settings = load_settings(env="development")
    assert settings.env == "development"


def test_load_settings_production_logging_level() -> None:
    settings = load_settings(env="production")
    assert settings.logging.level == "WARNING"


def test_load_settings_development_debug_true() -> None:
    settings = load_settings(env="development")
    assert settings.debug is True


def test_load_settings_env_var_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DI_LOGGING__LEVEL", "ERROR")
    settings = load_settings(env="development")
    assert settings.logging.level == "ERROR"


def test_load_settings_missing_env_yaml_does_not_raise(tmp_path: Path) -> None:
    import shutil
    project_root = Path(__file__).resolve().parent.parent.parent
    config_src = project_root / "config" / "default.yaml"
    shutil.copy(config_src, tmp_path / "default.yaml")
    # No staging.yaml in tmp_path — should succeed
    settings = load_settings(config_dir=tmp_path, env="staging")
    assert settings is not None


def test_load_settings_missing_default_yaml_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_settings(config_dir=tmp_path, env="development")


def test_load_yaml_returns_empty_dict_for_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("")
    result = load_yaml(empty)
    assert result == {}


def test_load_yaml_raises_on_malformed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(": invalid: yaml: [")
    with pytest.raises(ValueError):
        load_yaml(bad)


def test_merge_configs_deep_merge() -> None:
    base = {"a": 1, "nested": {"x": 1, "y": 2}}
    override = {"nested": {"y": 99, "z": 3}}
    result = merge_configs(base, override)
    assert result == {"a": 1, "nested": {"x": 1, "y": 99, "z": 3}}


def test_merge_configs_does_not_mutate_inputs() -> None:
    base = {"a": {"b": 1}}
    override = {"a": {"c": 2}}
    result = merge_configs(base, override)
    assert "c" not in base["a"]
    assert result["a"] == {"b": 1, "c": 2}


def test_merge_configs_lists_replaced_not_appended() -> None:
    base = {"items": [1, 2, 3]}
    override = {"items": [4, 5]}
    result = merge_configs(base, override)
    assert result["items"] == [4, 5]


def test_merge_configs_none_replaces_base_value() -> None:
    base = {"key": "value"}
    override = {"key": None}
    result = merge_configs(base, override)
    assert result["key"] is None
