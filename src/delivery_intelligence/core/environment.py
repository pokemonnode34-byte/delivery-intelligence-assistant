"""Environment management for Delivery Intelligence."""

from __future__ import annotations

import logging
import os
import platform
import sys

from dotenv import load_dotenv

_VALID_ENVIRONMENTS = frozenset({"development", "staging", "production"})
_REQUIRED_VARS: dict[str, list[str]] = {
    "development": [],
    "staging": ["DI_GITLAB__URL", "DI_GITLAB__TOKEN"],
    "production": ["DI_GITLAB__URL", "DI_GITLAB__TOKEN"],
}

logger = logging.getLogger(__name__)


def load_environment() -> str:
    """Load .env file and detect the current environment.

    Returns the environment name string ('development', 'staging', or 'production').
    Raises ValueError if DI_ENV is set to an invalid value.
    """
    load_dotenv(override=False)
    env = os.environ.get("DI_ENV", "development")
    if env not in _VALID_ENVIRONMENTS:
        raise ValueError(
            f"Invalid DI_ENV value '{env}'. Must be one of: {sorted(_VALID_ENVIRONMENTS)}"
        )
    return env


def validate_required_env_vars(env: str) -> None:
    """Validate required environment variables for the given environment.

    In 'development', this always succeeds (may log warnings).
    In 'staging' and 'production', raises EnvironmentError if any required
    variable is missing or empty, listing ALL missing variables.
    """
    if env == "development":
        gitlab_url = os.environ.get("DI_GITLAB__URL", "")
        gitlab_token = os.environ.get("DI_GITLAB__TOKEN", "")
        if not gitlab_url or not gitlab_token:
            logger.warning(
                "Missing GitLab credentials in development mode. "
                "Set DI_GITLAB__URL and DI_GITLAB__TOKEN for full functionality."
            )
        return

    required = _REQUIRED_VARS.get(env, [])
    missing = [var for var in required if not os.environ.get(var, "").strip()]

    if missing:
        raise EnvironmentError(
            f"Missing required environment variables for '{env}': {', '.join(missing)}"
        )


def get_environment_summary() -> dict[str, str]:
    """Return a safe summary dict of the current environment.

    Never includes secret values — only variable names and safe metadata.
    """
    return {
        "env": os.environ.get("DI_ENV", "development"),
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "debug": os.environ.get("DI_DEBUG", "false").lower(),
    }
