"""Tests for the logging system (Step 3)."""

import json

import pytest

import delivery_intelligence.core.logging as log_module
from delivery_intelligence.config.settings import LoggingSettings
from delivery_intelligence.core.logging import get_logger, setup_logging


@pytest.fixture(autouse=True)
def reset_logging_state() -> None:
    """Reset module-level logging flag before every test."""
    log_module._logging_configured = False


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    def test_configures_structlog_json(self) -> None:
        settings = LoggingSettings(format="json")
        setup_logging(settings)
        assert log_module._logging_configured is True

    def test_configures_structlog_console(self) -> None:
        settings = LoggingSettings(format="console")
        setup_logging(settings)
        assert log_module._logging_configured is True

    def test_second_call_is_no_op(self) -> None:
        settings = LoggingSettings(format="json")
        setup_logging(settings)
        # Calling a second time must not raise and must leave flag True
        setup_logging(settings)
        assert log_module._logging_configured is True

    def test_force_reinitializes(self) -> None:
        settings = LoggingSettings(format="json")
        setup_logging(settings)
        assert log_module._logging_configured is True
        setup_logging(settings, force=True)
        assert log_module._logging_configured is True

    def test_idempotent_single_log_line(self, capsys: pytest.CaptureFixture) -> None:
        """Calling setup_logging twice must not produce duplicate log lines."""
        settings = LoggingSettings(format="json")
        setup_logging(settings)
        setup_logging(settings)  # second call is a no-op
        logger = get_logger("idempotency_test")
        logger.info("check", value=1)
        captured = capsys.readouterr()
        non_empty_lines = [line for line in captured.out.strip().splitlines() if line.strip()]
        assert len(non_empty_lines) == 1


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------


class TestGetLogger:
    def test_returns_bound_logger(self) -> None:
        setup_logging(LoggingSettings(format="json"))
        logger = get_logger("module_name")
        assert logger is not None

    def test_logger_name_key_present(self, capsys: pytest.CaptureFixture) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("my_module")
        logger.info("test_event")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output["logger_name"] == "my_module"

    def test_json_output_has_required_keys(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("key_test")
        logger.info("my_event", extra_field="x")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert "timestamp" in output
        assert "level" in output
        assert "logger_name" in output
        assert "event" in output


# ---------------------------------------------------------------------------
# Sensitive field redaction
# ---------------------------------------------------------------------------


class TestSensitiveFieldRedaction:
    def test_token_is_redacted(self, capsys: pytest.CaptureFixture) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("security")
        logger.info("auth", token="super-secret-token")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output["token"] == "****REDACTED****"
        assert "super-secret-token" not in captured.out

    def test_password_is_redacted(self, capsys: pytest.CaptureFixture) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("security")
        logger.info("login", password="mypassword123")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output["password"] == "****REDACTED****"

    def test_secret_is_redacted(self, capsys: pytest.CaptureFixture) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("security")
        logger.info("vault", secret="vault-value")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output["secret"] == "****REDACTED****"

    def test_authorization_is_redacted(self, capsys: pytest.CaptureFixture) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("security")
        logger.info("req", authorization="Bearer abc")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output["authorization"] == "****REDACTED****"

    def test_credential_is_redacted(self, capsys: pytest.CaptureFixture) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("security")
        logger.info("svc", credential="cred-value")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output["credential"] == "****REDACTED****"

    def test_non_sensitive_fields_pass_through(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("clean")
        logger.info("event", project_id=42, status="active")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output["project_id"] == 42
        assert output["status"] == "active"

    def test_case_insensitive_key_matching(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        setup_logging(LoggingSettings(format="json"), force=True)
        logger = get_logger("security")
        logger.info("event", ACCESS_TOKEN="abc", User_Password="xyz")
        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())
        assert output["ACCESS_TOKEN"] == "****REDACTED****"
        assert output["User_Password"] == "****REDACTED****"
