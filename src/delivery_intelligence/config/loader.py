"""Configuration loader: reads YAML files, merges them, and produces AppSettings.

This is the single entry point for obtaining a fully validated
:class:`~delivery_intelligence.config.settings.AppSettings` instance.
"""

import copy
from pathlib import Path
from typing import Any

import structlog
import yaml

from delivery_intelligence.config.settings import AppSettings

_logger = structlog.get_logger(__name__)


def load_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML file and return its contents as a dict.

    Raises :class:`FileNotFoundError` if the file does not exist.
    Raises :class:`ValueError` if the YAML is malformed.
    Returns an empty dict for an empty file.
    """
    if not path.exists():
        raise FileNotFoundError(f"YAML config file not found: {path}")
    try:
        with path.open() as fh:
            result = yaml.safe_load(fh)
            return result if result is not None else {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML file '{path}': {exc}") from exc


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge *override* on top of *base* and return a new dict.

    Rules:
    - Nested dicts are merged recursively.
    - Lists are replaced entirely (not appended).
    - ``None`` values in *override* explicitly replace base values.
    - Neither input dict is mutated.
    """
    result: dict[str, Any] = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_settings(
    config_dir: Path | None = None,
    env: str | None = None,
) -> AppSettings:
    """Load, merge, and validate configuration for the given environment.

    Resolution order (highest wins):
    1. Environment variables (handled by Pydantic Settings internally).
    2. Environment-specific YAML (e.g. ``config/production.yaml``).
    3. Default YAML (``config/default.yaml``).
    4. Pydantic field defaults.

    Args:
        config_dir: Path to the ``config/`` directory.  Defaults to the
            ``config/`` directory in the project root.
        env: Environment name override.  When omitted,
            :func:`~delivery_intelligence.core.environment.load_environment`
            is called to detect the active environment.

    Raises:
        FileNotFoundError: If ``config/default.yaml`` is missing.
        ValueError: If any YAML file is malformed.
    """
    if env is None:
        # Deferred import to respect the no-circular-import rule while still
        # supporting standalone calls to load_settings() without an env arg.
        from delivery_intelligence.core.environment import (  # noqa: PLC0415
            load_environment,
        )

        env = load_environment()

    if config_dir is None:
        # Resolve relative to this file:
        # src/delivery_intelligence/config/loader.py -> project root -> config/
        config_dir = Path(__file__).parent.parent.parent.parent / "config"

    default_path = config_dir / "default.yaml"
    if not default_path.exists():
        raise FileNotFoundError(
            f"Required default config file not found: {default_path}"
        )

    base_config = load_yaml(default_path)

    env_path = config_dir / f"{env}.yaml"
    env_config: dict[str, Any] = {}
    if env_path.exists():
        env_config = load_yaml(env_path)

    merged = merge_configs(base_config, env_config)

    settings = AppSettings(**merged)

    _logger.info(
        "configuration_loaded",
        env=settings.env,
        app_name=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        logging_level=settings.logging.level,
        logging_format=settings.logging.format,
    )
    return settings
