"""Tests for the configuration settings models (Step 2) and loader (Step 7)."""

import textwrap
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from delivery_intelligence.config.loader import load_settings, load_yaml, merge_configs
from delivery_intelligence.config.settings import (
    AppSettings,
    DatabaseSettings,
    GitLabSettings,
    LoggingSettings,
)


# ---------------------------------------------------------------------------
# GitLabSettings
# ---------------------------------------------------------------------------


class TestGitLabSettings:
    def test_default_values(self) -> None:
        s = GitLabSettings(url="https://gitlab.example.com", token=SecretStr("t"))
        assert s.url == "https://gitlab.example.com"
        assert s.api_version == "v4"
        assert s.timeout == 30
        assert s.max_retries == 3
        assert s.per_page == 100

    def test_strips_trailing_slash(self) -> None:
        s = GitLabSettings(url="https://gitlab.example.com/", token=SecretStr("t"))
        assert s.url == "https://gitlab.example.com"

    def test_per_page_too_high_raises(self) -> None:
        with pytest.raises(ValidationError):
            GitLabSettings(
                url="https://gitlab.example.com", token=SecretStr("t"), per_page=200
            )

    def test_per_page_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            GitLabSettings(
                url="https://gitlab.example.com", token=SecretStr("t"), per_page=0
            )

    def test_per_page_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            GitLabSettings(
                url="https://gitlab.example.com", token=SecretStr("t"), per_page=-1
            )

    def test_per_page_boundary_values_valid(self) -> None:
        low = GitLabSettings(
            url="https://gitlab.example.com", token=SecretStr("t"), per_page=1
        )
        high = GitLabSettings(
            url="https://gitlab.example.com", token=SecretStr("t"), per_page=100
        )
        assert low.per_page == 1
        assert high.per_page == 100

    def test_timeout_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            GitLabSettings(
                url="https://gitlab.example.com", token=SecretStr("t"), timeout=0
            )

    def test_timeout_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            GitLabSettings(
                url="https://gitlab.example.com", token=SecretStr("t"), timeout=-5
            )

    def test_token_not_in_repr(self) -> None:
        s = GitLabSettings(
            url="https://gitlab.example.com", token=SecretStr("supersecret")
        )
        assert "supersecret" not in repr(s)
        assert "supersecret" not in str(s)


# ---------------------------------------------------------------------------
# LoggingSettings
# ---------------------------------------------------------------------------


class TestLoggingSettings:
    def test_default_values(self) -> None:
        s = LoggingSettings()
        assert s.level == "INFO"
        assert s.format == "json"
        assert s.output == "stdout"
        assert s.file_path is None

    def test_invalid_level_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoggingSettings(level="INVALID")  # type: ignore[arg-type]

    def test_file_output_without_path_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoggingSettings(output="file", file_path=None)

    def test_file_output_with_path_valid(self) -> None:
        s = LoggingSettings(output="file", file_path=Path("/tmp/app.log"))
        assert s.file_path == Path("/tmp/app.log")


# ---------------------------------------------------------------------------
# DatabaseSettings
# ---------------------------------------------------------------------------


class TestDatabaseSettings:
    def test_default_values(self) -> None:
        s = DatabaseSettings()
        assert s.url == "sqlite:///delivery_intelligence.db"
        assert s.echo is False


# ---------------------------------------------------------------------------
# AppSettings
# ---------------------------------------------------------------------------


class TestAppSettings:
    def test_default_values(self) -> None:
        s = AppSettings()
        assert s.env == "development"
        assert s.app_name == "delivery-intelligence"
        assert s.version == "0.1.0"
        assert s.debug is False

    def test_logging_level_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DI_LOGGING__LEVEL", "DEBUG")
        s = AppSettings()
        assert s.logging.level == "DEBUG"

    def test_invalid_logging_level_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DI_LOGGING__LEVEL", "INVALID")
        with pytest.raises(ValidationError):
            AppSettings()

    def test_gitlab_url_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DI_GITLAB__URL", "https://custom.gitlab.com")
        s = AppSettings()
        assert s.gitlab.url == "https://custom.gitlab.com"

    def test_model_dump_does_not_expose_token(self) -> None:
        s = AppSettings()
        dumped = str(s.model_dump())
        assert "not-set" not in dumped


# ---------------------------------------------------------------------------
# load_yaml
# ---------------------------------------------------------------------------


class TestLoadYaml:
    def test_reads_valid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "conf.yaml"
        f.write_text("key: value\nnested:\n  a: 1\n")
        result = load_yaml(f)
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("")
        assert load_yaml(f) == {}

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_yaml(tmp_path / "nonexistent.yaml")

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text("key: [\nunclosed bracket")
        with pytest.raises(ValueError, match="Malformed YAML"):
            load_yaml(f)


# ---------------------------------------------------------------------------
# merge_configs
# ---------------------------------------------------------------------------


class TestMergeConfigs:
    def test_basic_override(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = merge_configs(base, override)
        assert result == {"a": 1, "b": 99}

    def test_nested_deep_merge(self) -> None:
        base = {"logging": {"level": "INFO", "format": "json"}}
        override = {"logging": {"level": "DEBUG"}}
        result = merge_configs(base, override)
        assert result == {"logging": {"level": "DEBUG", "format": "json"}}

    def test_list_replaced_entirely(self) -> None:
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = merge_configs(base, override)
        assert result["items"] == [4, 5]

    def test_none_override_replaces_base(self) -> None:
        base = {"key": "value"}
        override = {"key": None}
        result = merge_configs(base, override)
        assert result["key"] is None

    def test_does_not_mutate_inputs(self) -> None:
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}
        merge_configs(base, override)
        assert base == {"a": {"b": 1}}
        assert override == {"a": {"b": 2}}

    def test_new_keys_from_override_added(self) -> None:
        base = {"a": 1}
        override = {"b": 2}
        result = merge_configs(base, override)
        assert result == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# load_settings
# ---------------------------------------------------------------------------


class TestLoadSettings:
    def _write_yaml(self, path: Path, content: str) -> None:
        path.write_text(textwrap.dedent(content))

    def test_loads_defaults(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path / "default.yaml",
            """
            env: development
            app_name: delivery-intelligence
            version: "0.1.0"
            debug: false
            gitlab:
              url: "https://gitlab.example.com"
              token: "not-set"
              api_version: "v4"
              timeout: 30
              max_retries: 3
              per_page: 100
            logging:
              level: "INFO"
              format: "json"
              output: "stdout"
            database:
              url: "sqlite:///delivery_intelligence.db"
              echo: false
            """,
        )
        settings = load_settings(config_dir=tmp_path, env="development")
        assert settings.env == "development"

    def test_env_override_yaml_merged(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path / "default.yaml",
            """
            env: development
            app_name: delivery-intelligence
            version: "0.1.0"
            debug: false
            gitlab:
              url: "https://gitlab.example.com"
              token: "not-set"
              api_version: "v4"
              timeout: 30
              max_retries: 3
              per_page: 100
            logging:
              level: "INFO"
              format: "json"
              output: "stdout"
            database:
              url: "sqlite:///delivery_intelligence.db"
              echo: false
            """,
        )
        self._write_yaml(
            tmp_path / "production.yaml",
            """
            env: production
            logging:
              level: "WARNING"
              format: "json"
            """,
        )
        settings = load_settings(config_dir=tmp_path, env="production")
        assert settings.logging.level == "WARNING"
        assert settings.env == "production"

    def test_missing_default_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_settings(config_dir=tmp_path, env="development")

    def test_missing_env_specific_yaml_is_ok(self, tmp_path: Path) -> None:
        self._write_yaml(
            tmp_path / "default.yaml",
            """
            env: development
            app_name: delivery-intelligence
            version: "0.1.0"
            debug: false
            gitlab:
              url: "https://gitlab.example.com"
              token: "not-set"
              api_version: "v4"
              timeout: 30
              max_retries: 3
              per_page: 100
            logging:
              level: "INFO"
              format: "json"
              output: "stdout"
            database:
              url: "sqlite:///delivery_intelligence.db"
              echo: false
            """,
        )
        # 'custom' has no matching YAML file — must not raise
        settings = load_settings(config_dir=tmp_path, env="development")
        assert settings is not None

    def test_env_var_overrides_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._write_yaml(
            tmp_path / "default.yaml",
            """
            env: development
            app_name: delivery-intelligence
            version: "0.1.0"
            debug: false
            gitlab:
              url: "https://gitlab.example.com"
              token: "not-set"
              api_version: "v4"
              timeout: 30
              max_retries: 3
              per_page: 100
            logging:
              level: "INFO"
              format: "json"
              output: "stdout"
            database:
              url: "sqlite:///delivery_intelligence.db"
              echo: false
            """,
        )
        monkeypatch.setenv("DI_LOGGING__LEVEL", "ERROR")
        settings = load_settings(config_dir=tmp_path, env="development")
        assert settings.logging.level == "ERROR"
