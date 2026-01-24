"""State management using JSON."""

import json
from pathlib import Path
from typing import Any

from src.config import STATE_FILE

# Maximum number of recent directories to keep
MAX_RECENT_DIRECTORIES = 10


def add_recent_directory(directories: list[str], new_directory: str) -> list[str]:
    """Add a directory to recent directories list, removing duplicates and limiting count."""
    # Remove if already exists
    directories = [d for d in directories if d != new_directory]
    # Add to front
    directories.insert(0, new_directory)
    # Limit to max
    return directories[:MAX_RECENT_DIRECTORIES]


def load_state() -> dict[str, Any]:
    """Load application state from JSON file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Convert selected_files list back to set
                if "selected_files" in data and isinstance(
                    data["selected_files"], list
                ):
                    data["selected_files"] = set(
                        tuple(f) for f in data["selected_files"]
                    )
                return data
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "selected_files": set(),
        "select_all_state": False,
        "recent_directories": [],
    }


def save_state(
    selected_files: set[tuple[str, str]],
    select_all_state: bool,
    recent_directories: list[str] | None = None,
) -> bool:
    """Save application state to JSON file. Returns True on success, False on failure."""
    if recent_directories is None:
        recent_directories = []
    state = {
        "selected_files": [
            list(f) for f in selected_files
        ],  # Convert set to list for JSON
        "select_all_state": select_all_state,
        "recent_directories": recent_directories,
    }

    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return True
    except IOError as e:
        print(f"Failed to save state: {e}")
        return False
