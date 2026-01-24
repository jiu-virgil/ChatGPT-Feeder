"""Configuration constants and paths."""

import os
import sys
from pathlib import Path
from typing import Final

# Application info
APP_NAME: Final[str] = "Spoon"
APP_VERSION: Final[str] = "1.0.0"
APP_DESCRIPTION: Final[str] = "Feed your code files to ChatGPT with ease"

# Paths - handle both development and bundled executable
if getattr(sys, "frozen", False):
    # Running as bundled executable
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller
        BASE_DIR = Path(sys._MEIPASS)
    else:
        # Nuitka or other bundler - use executable directory
        BASE_DIR = Path(sys.executable).parent
else:
    # Running in development mode
    # Try multiple path resolution strategies
    # 1. Relative to this file (most reliable)
    base_from_file = Path(__file__).parent.parent

    # 2. Relative to current working directory (fallback)
    base_from_cwd = Path.cwd()

    # Use file-based path if it exists and has resources, otherwise try CWD
    if (base_from_file / "resources").exists():
        BASE_DIR = base_from_file
    elif (base_from_cwd / "resources").exists():
        BASE_DIR = base_from_cwd
    else:
        # Default to file-based path
        BASE_DIR = base_from_file

RESOURCES_DIR: Final[Path] = BASE_DIR / "resources"
# Use ICO file for better compatibility (works in both Qt and Windows)
ICON_PATH: Final[Path] = RESOURCES_DIR / "spoon.ico"
# Fallback to PNG if ICO doesn't exist (for development)
if not ICON_PATH.exists():
    ICON_PATH = RESOURCES_DIR / "spoon.png"
STYLES_PATH: Final[Path] = RESOURCES_DIR / "styles.qss"
ICONS_DIR: Final[Path] = RESOURCES_DIR / "icons"

# State file (JSON instead of pickle)
STATE_FILE: Final[Path] = Path(
    os.path.join(os.path.expanduser("~"), ".spoon_state.json")
)

# Default settings
DEFAULT_EXTENSION: Final[str] = ".py"
DEFAULT_IGNORE_PATTERNS: Final[list[str]] = [
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "*.pyc",
    "*.pyo",
    "*.pyd",
]

# Standard file filters for UI (when "Use Standard Filters" is enabled)
# These are applied to file names in the tree view
STANDARD_FILE_NAME_PREFIXES: Final[list[str]] = [
    ".",  # Hidden files (e.g., .git, .env, .config)
    "__",  # Python package files (e.g., __pycache__, __init__.pyc)
]

STANDARD_FILE_NAMES: Final[list[str]] = [
    "__pycache__",
    "__init__.pyc",
]

STANDARD_DIRECTORY_NAMES: Final[list[str]] = [
    "node_modules",
    ".git",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".mypy",
    "dist",
    "build",
    ".build",
    ".tox",
    ".coverage",
    ".nyc_output",
    "coverage",
    ".cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    ".vs",
    "target",  # Rust/Cargo
    "out",  # TypeScript/JavaScript build output
    ".next",  # Next.js
    ".nuxt",  # Nuxt.js
    ".svelte-kit",  # SvelteKit
]

# File scanning limits
MAX_FILES_WARNING: Final[int] = 10000  # Show warning if more than this many files
MAX_FILES_HARD_LIMIT: Final[int] = (
    50000  # Hard limit - refuse to scan if more than this
)
MAX_FILES_PER_DIRECTORY: Final[int] = (
    5000  # Lock directories with more than this many files
)
