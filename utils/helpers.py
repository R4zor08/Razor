"""General helper functions."""

import os


def ensure_dir(path: str) -> str:
    """Create a directory if it does not exist and return the path."""
    os.makedirs(path, exist_ok=True)
    return path
