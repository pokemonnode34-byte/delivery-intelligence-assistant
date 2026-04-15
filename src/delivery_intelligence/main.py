"""Application entry point for Delivery Intelligence.

:func:`bootstrap` wires the full system together.  :func:`main` is the
CLI-style guard that calls ``bootstrap`` and handles fatal errors.
"""

import sys
from pathlib import Path

from delivery_intelligence.config.loader import load_settings
from delivery_intelligence.core.container import Container, create_container
from delivery_intelligence.core.environment import (
    load_environment,
    validate_required_env_vars,
)
from delivery_intelligence.core.logging import get_logger


def bootstrap(config_dir: Path | None = None) -> Container:
    """Initialise the full application stack and return a ready container.

    Steps:
    1. Detect the active environment.
    2. Validate required environment variables (fail-fast in production).
    3. Load and merge configuration from YAML and environment variables.
    4. Build and initialise the dependency container.

    Args:
        config_dir: Optional override for the ``config/`` directory path.

    Returns:
        An initialised :class:`~delivery_intelligence.core.container.Container`.
    """
    env = load_environment()
    validate_required_env_vars(env)
    settings = load_settings(config_dir=config_dir, env=env)
    container = create_container(settings)
    container.initialize()
    logger = get_logger("main")
    logger.info(
        "delivery_intelligence_initialized",
        env=env,
        version=settings.version,
    )
    return container


def main() -> None:
    """Run the bootstrap sequence and log the system-ready state.

    Exits with code 1 on :class:`EnvironmentError` or any unexpected
    exception.
    """
    try:
        bootstrap()
        logger = get_logger("main")
        logger.info("delivery_intelligence_ready")
    except EnvironmentError as exc:
        print(f"Environment error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
