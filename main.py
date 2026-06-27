"""Razor AI — entry point."""

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Bootstrap and run the assistant."""
    logger.info("Starting %s v%s", config.APP_NAME, config.APP_VERSION)
    logger.info("Phase 0 — project initialized (no logic yet)")


if __name__ == "__main__":
    main()
