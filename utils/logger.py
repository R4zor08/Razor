"""Logging utilities."""

import logging
import os

import config


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance."""
    os.makedirs(config.LOGS_DIR, exist_ok=True)

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)

    return logger
