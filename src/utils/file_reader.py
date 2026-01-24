"""File reading utilities."""
import os
import subprocess
import sys
from pathlib import Path


def read_file_content(file_path: Path | str) -> str:
    """Read file content with UTF-8 encoding. Returns error message as comment on failure."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"# Error reading file: {e}"


def collect_files_content(file_paths: list[Path | str]) -> dict[str, str]:
    """Collect content from multiple files."""
    content_map: dict[str, str] = {}
    for file_path in file_paths:
        path = Path(file_path)
        if path.exists() and path.is_file():
            content_map[str(path)] = read_file_content(path)
    return content_map


def open_file_in_editor(file_path: Path | str) -> bool:
    """Open file in default system editor. Returns True on success, False on failure."""
    try:
        path_str = str(file_path)
        if sys.platform == "win32":
            os.startfile(path_str)
        elif sys.platform == "darwin":
            subprocess.run(["open", path_str], check=False)
        else:
            subprocess.run(["xdg-open", path_str], check=False)
        return True
    except Exception as e:
        # Error is logged but not raised - caller can check return value
        print(f"Failed to open file '{file_path}': {e}")
        return False


