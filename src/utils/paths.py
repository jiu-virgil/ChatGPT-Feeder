"""Path validation and utility functions."""

import os
from pathlib import Path


def validate_directory_path(path_str: str) -> tuple[bool, Path | None, str | None]:
    """Validate that a path string is a valid, existing directory.

    Args:
        path_str: Path string to validate

    Returns:
        Tuple of (is_valid, path_object, error_message)
        - is_valid: True if path is valid directory, False otherwise
        - path_object: Path object if valid, None otherwise
        - error_message: Error message if invalid, None otherwise
    """
    if not path_str:
        return False, None, "Path is empty"

    try:
        path = Path(path_str).resolve()

        if not path.exists():
            return False, None, f"Path does not exist: {path_str}"

        if not path.is_dir():
            return False, None, f"Path is not a directory: {path_str}"

        return True, path, None

    except Exception as e:
        return False, None, f"Failed to validate path: {str(e)}"


def shorten_home_path(path_str: str) -> str:
    """Shorten path by replacing home directory with ~.

    Args:
        path_str: Path string to shorten

    Returns:
        Shortened path string with ~ replacing home directory if applicable
    """
    if not path_str:
        return path_str

    try:
        home_dir = str(Path.home())
        # Normalize paths for comparison
        path_resolved = str(Path(path_str).expanduser().resolve())
        home_resolved = str(Path(home_dir).expanduser().resolve())

        # Check if path starts with home directory
        if path_resolved.startswith(home_resolved):
            # Replace home directory with ~
            remaining = path_resolved[len(home_resolved) :].lstrip(os.sep)
            if remaining:
                return f"~{os.sep}{remaining}"
            else:
                return "~"

        return path_str
    except Exception:
        # If anything fails, return original path
        return path_str
