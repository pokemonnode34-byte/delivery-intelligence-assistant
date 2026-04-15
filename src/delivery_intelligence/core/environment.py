"""Environment detection and validation utilities.

This module handles .env file loading, environment name detection, and
fail-fast validation of required environment variables.  It never logs
or exposes secret values — only variable names appear in error messages.
"""

import os
import platform
import sys

import structlog
from dotenv import load_dotenv

_logger = structlog.get_logger(__name__)

_VALID_ENVIRONMENTS: frozenset[str] = frozenset(
    {"development", "staging", "production"}
)

_REQUIRED_VARS: dict[str, list[str]] = {
    "development": [],
    "staging": ["DI_GITLAB__URL", "DI_GITLAB__TOKEN"],
    "production": ["DI_GITLAB__URL", "DI_GITLAB__TOKEN"],
}


def load_environment() -> str:
    """Load the .env file (if present) and return the active environment name.

    Returns ``"development"`` when ``DI_ENV`` is not set.
    Raises :class:`ValueError` for invalid environment names.
    """
    load_dotenv(override=False)
    env = os.environ.get("DI_ENV", "development")
    if env not in _VALID_ENVIRONMENTS:
        raise ValueError(
            f"Invalid DI_ENV value: '{env}'. "
            f"Must be one of: {', '.join(sorted(_VALID_ENVIRONMENTS))}"
        )
    return env


def validate_required_env_vars(env: str) -> None:
    """Validate that all required environment variables are present for *env*.

    In development, this always succeeds (missing GitLab credentials
    produce a warning only).  In staging and production, missing variables
    raise :class:`EnvironmentError` listing every missing name.
    """
    if env == "development":
        for var in ["DI_GITLAB__URL", "DI_GITLAB__TOKEN"]:
            if not os.environ.get(var):
                _logger.warning(
                    "missing_gitlab_credential_in_development", variable=var
                )
        return

    required = _REQUIRED_VARS.get(env, [])
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        missing_list = ", ".join(missing)
        raise EnvironmentError(
            f"Missing required environment variables for '{env}': {missing_list}"
        )


def get_environment_summary() -> dict[str, str]:
    """Return a safe summary of the current runtime environment.

    All values are strings.  Secret values are never included.
    """
    raw_debug = os.environ.get("DI_DEBUG", "false").lower()
    debug_value = "true" if raw_debug in ("1", "true", "yes") else "false"
    return {
        "env": os.environ.get("DI_ENV", "development"),
        "python_version": sys.version,
        "platform": platform.platform(),
        "debug": debug_value,
    }
