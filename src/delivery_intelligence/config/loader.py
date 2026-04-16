"""Configuration loader: reads YAML files, merges, validates, and returns AppSettings."""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

from delivery_intelligence.config.settings import AppSettings
from delivery_intelligence.core.environment import load_environment

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_CONFIG_DIR = _PROJECT_ROOT / "config"


def load_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file and return its contents as a dict.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the YAML is malformed.
    Returns an empty dict if the file is empty.
    """
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Malformed YAML in {path}: {e}") from e
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ValueError(f"Expected a YAML mapping at {path}, got {type(content).__name__}")
    return content


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge two config dicts. Override values replace base values.

    Nested dicts are merged recursively. Lists are replaced entirely.
    None values in override DO replace base values. Does not mutate inputs.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_settings(config_dir: Path | None = None, env: str | None = None) -> AppSettings:
    """Load and validate application settings from YAML files and environment variables.

    1. Detects the environment (or uses the env parameter if provided).
    2. Loads config/default.yaml as base. Raises FileNotFoundError if missing.
    3. Loads config/{env}.yaml as override (optional, skipped if missing).
    4. Deep-merges environment config over default.
    5. Passes merged dict into AppSettings (Pydantic Settings applies env var overrides).
    6. Returns the validated AppSettings instance.
    """
    resolved_env = env if env is not None else load_environment()
    resolved_dir = config_dir if config_dir is not None else _DEFAULT_CONFIG_DIR

    default_path = resolved_dir / "default.yaml"
    base_config = load_yaml(default_path)

    env_path = resolved_dir / f"{resolved_env}.yaml"
    if env_path.exists():
        env_config = load_yaml(env_path)
        merged = merge_configs(base_config, env_config)
    else:
        merged = base_config

    settings = AppSettings(**merged)
    logger.info(
        "Configuration loaded: env=%s app_name=%s version=%s",
        settings.env,
        settings.app_name,
        settings.version,
    )
    return settings
