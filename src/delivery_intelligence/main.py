"""Main entry point for Delivery Intelligence."""

from __future__ import annotations

import sys
from pathlib import Path

from delivery_intelligence.config.loader import load_settings
from delivery_intelligence.core.container import Container, create_container
from delivery_intelligence.core.environment import load_environment, validate_required_env_vars
from delivery_intelligence.core.logging import get_logger


def bootstrap(config_dir: Path | None = None) -> Container:
    """Bootstrap the Delivery Intelligence system.

    1. Detects the environment.
    2. Validates required environment variables.
    3. Loads typed settings.
    4. Creates and initializes the container.
    5. Returns the ready container.
    """
    env = load_environment()
    validate_required_env_vars(env)
    settings = load_settings(config_dir=config_dir, env=env)
    container = create_container(settings)
    container.initialize()
    logger = container.get_logger("main")
    logger.info(
        "delivery_intelligence_initialized",
        env=env,
        version=settings.version,
    )
    return container


def main() -> None:
    """Run the Delivery Intelligence bootstrap as a standalone process."""
    try:
        container = bootstrap()
        logger = container.get_logger("main")
        logger.info("system_ready")
    except EnvironmentError as e:
        logger = get_logger("main")
        logger.error("startup_failed_environment_error", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger = get_logger("main")
        logger.error("startup_failed_unexpected_error", error_type=type(e).__name__, error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
