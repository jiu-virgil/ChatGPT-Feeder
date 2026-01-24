"""File scanning utilities."""

import fnmatch
import os
from pathlib import Path

from src.config import DEFAULT_IGNORE_PATTERNS
from src.utils.extensions import matches_extension

# Cache for .gitignore patterns per directory
# Format: {directory_path: (patterns_list, modification_time)}
_gitignore_cache: dict[str, tuple[list[str], float]] = {}

# Cache for compiled ignore patterns
# Format: {pattern: compiled_pattern_function}
_compiled_pattern_cache: dict[str, callable] = {}


def _load_gitignore_patterns(root_dir: Path) -> list[str]:
    """Load .gitignore patterns with caching based on file modification time.

    Returns:
        List of patterns from .gitignore file, or empty list if file doesn't exist.
    """
    gitignore_path = root_dir / ".gitignore"
    if not gitignore_path.exists():
        return []

    # Check cache
    dir_key = str(root_dir.resolve())
    try:
        mtime = gitignore_path.stat().st_mtime
        if dir_key in _gitignore_cache:
            cached_patterns, cached_mtime = _gitignore_cache[dir_key]
            if cached_mtime == mtime:
                # Cache hit - return cached patterns
                return cached_patterns.copy()
    except (OSError, ValueError):
        # File might have been deleted or permission error
        _gitignore_cache.pop(dir_key, None)
        return []

    # Cache miss or file changed - read and parse
    patterns = []
    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)

        # Update cache
        try:
            mtime = gitignore_path.stat().st_mtime
            _gitignore_cache[dir_key] = (patterns.copy(), mtime)
        except (OSError, ValueError):
            pass  # Cache update failed, but we still return patterns
    except Exception:
        pass  # Ignore errors reading .gitignore

    return patterns


def _compile_pattern(pattern: str) -> callable:
    """Compile an ignore pattern into a matching function with caching."""
    if pattern in _compiled_pattern_cache:
        return _compiled_pattern_cache[pattern]

    # Normalize pattern: handle common cases
    pattern_normalized = pattern.strip()

    # Create matching function
    if "*" in pattern_normalized or "?" in pattern_normalized:
        # Use fnmatch for wildcard patterns
        def match_func(path_str: str) -> bool:
            # Try matching against full path and basename
            return (
                fnmatch.fnmatch(path_str, pattern_normalized)
                or fnmatch.fnmatch(os.path.basename(path_str), pattern_normalized)
                or fnmatch.fnmatch(path_str, f"*{pattern_normalized}")
                or path_str.endswith(pattern_normalized)
            )

    else:
        # Simple string matching for non-wildcard patterns
        def match_func(path_str: str) -> bool:
            return (
                pattern_normalized in path_str
                or path_str.endswith(pattern_normalized)
                or os.path.basename(path_str) == pattern_normalized
            )

    # Cache compiled function
    _compiled_pattern_cache[pattern] = match_func
    return match_func


def should_ignore(path: Path, ignore_patterns: list[str]) -> bool:
    """Check if a path should be ignored based on patterns.

    Uses compiled pattern matching with caching for better performance.
    """
    path_str = str(path)
    # Also try normalized path (forward slashes) for cross-platform compatibility
    path_str_normalized = path_str.replace("\\", "/")

    for pattern in ignore_patterns:
        match_func = _compile_pattern(pattern)
        if match_func(path_str) or match_func(path_str_normalized):
            return True
    return False


def count_files(
    root_dir: Path = Path("."),
    extension: str = ".py",
    ignore_patterns: list[str] | None = None,
    max_count: int | None = None,
) -> int:
    """Count files with given extension, excluding ignored paths.

    Args:
        root_dir: Root directory to scan
        extension: File extension to count (e.g., ".py")
        ignore_patterns: List of patterns to ignore
        max_count: If provided, stop counting once this number is reached (for performance)

    Returns:
        Number of files found (or max_count if reached)
    """
    if ignore_patterns is None:
        ignore_patterns = DEFAULT_IGNORE_PATTERNS.copy()
    else:
        ignore_patterns = ignore_patterns.copy()

    # Load .gitignore patterns (cached)
    gitignore_patterns = _load_gitignore_patterns(root_dir)
    ignore_patterns.extend(gitignore_patterns)

    count = 0
    for root, dirs, filenames in os.walk(root_dir):
        # Filter out ignored directories
        dirs[:] = [
            d for d in dirs if not should_ignore(Path(root) / d, ignore_patterns)
        ]

        for filename in filenames:
            file_path = Path(root) / filename
            if matches_extension(file_path.suffix, extension) and not should_ignore(
                file_path, ignore_patterns
            ):
                count += 1
                if max_count is not None and count >= max_count:
                    return count

    return count


def scan_files(
    root_dir: Path = Path("."),
    extension: str = ".py",
    ignore_patterns: list[str] | None = None,
    check_limit: int | None = None,
    collect_extensions: bool = True,
    use_standard_filters: bool = True,
) -> tuple[list[Path], int, dict[Path, int], dict[str, int]]:
    """Scan for files with given extension, excluding ignored paths.

    Args:
        root_dir: Root directory to scan
        extension: File extension to scan for (e.g., ".py")
        ignore_patterns: List of patterns to ignore
        check_limit: If provided, stop scanning and return early once this count is reached
        collect_extensions: If True, also collect extension counts for all files (not just the target extension)
        use_standard_filters: If True, also filter out files in STANDARD_DIRECTORY_NAMES
            and files matching STANDARD_FILE_NAME_PREFIXES/STANDARD_FILE_NAMES when collecting extensions

    Returns:
        Tuple of (list of file paths, total count found or limit reached, directory file counts, extension counts)
        - directory file counts: dict mapping directory Path to number of files in that directory
        - extension counts: dict mapping extension (with dot) to occurrence count, sorted by count
    """
    if ignore_patterns is None:
        ignore_patterns = DEFAULT_IGNORE_PATTERNS.copy()
    else:
        ignore_patterns = ignore_patterns.copy()

    # Load .gitignore patterns (cached)
    gitignore_patterns = _load_gitignore_patterns(root_dir)
    ignore_patterns.extend(gitignore_patterns)

    # Import standard filters if needed
    if use_standard_filters:
        from src.config import (
            STANDARD_DIRECTORY_NAMES,
            STANDARD_FILE_NAME_PREFIXES,
            STANDARD_FILE_NAMES,
        )
    else:
        STANDARD_DIRECTORY_NAMES = []
        STANDARD_FILE_NAME_PREFIXES = []
        STANDARD_FILE_NAMES = []

    files: list[Path] = []
    count = 0
    directory_counts: dict[Path, int] = {}  # Track file count per directory
    extension_counts: dict[str, int] = {}  # Track extension counts for all files

    for root, dirs, filenames in os.walk(root_dir):
        # Filter out ignored directories
        dirs[:] = [
            d for d in dirs if not should_ignore(Path(root) / d, ignore_patterns)
        ]

        # Also filter out standard directories if use_standard_filters is enabled
        if use_standard_filters:
            dirs[:] = [d for d in dirs if d not in STANDARD_DIRECTORY_NAMES]

        current_dir = Path(root)
        dir_file_count = 0

        for filename in filenames:
            file_path = Path(root) / filename
            if should_ignore(file_path, ignore_patterns):
                continue

            # Apply standard filters if enabled (for extension collection)
            should_ignore_file = False
            if use_standard_filters:
                file_name = file_path.name

                # Check standard prefixes (e.g., ".", "__")
                for prefix in STANDARD_FILE_NAME_PREFIXES:
                    if file_name.startswith(prefix):
                        should_ignore_file = True
                        break

                # Check standard file names (exact matches)
                if not should_ignore_file and file_name in STANDARD_FILE_NAMES:
                    should_ignore_file = True

                # Check if file is in a standard directory
                if not should_ignore_file:
                    # Check if any parent directory matches standard directory names
                    for parent in file_path.parents:
                        if parent.name in STANDARD_DIRECTORY_NAMES:
                            should_ignore_file = True
                            break

            # Collect extension information for all files (if enabled)
            # Only count if file is not filtered out by standard filters
            if collect_extensions and not should_ignore_file:
                ext = file_path.suffix
                if ext:  # Only count files with extensions
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1

            # Check if this file matches our target extension
            # If extension is empty string, include all files
            # Support comma-separated extensions
            if not extension or matches_extension(file_path.suffix, extension):
                count += 1
                dir_file_count += 1
                if check_limit is not None and count > check_limit:
                    # Return early if we've exceeded the limit
                    directory_counts[current_dir] = dir_file_count
                    return files, count, directory_counts, extension_counts
                files.append(file_path)

        # Store count for this directory (even if 0, for completeness)
        if dir_file_count > 0:
            directory_counts[current_dir] = dir_file_count

    # Return extension_counts dict (not sorted list) so caller can filter by count
    return sorted(files), count, directory_counts, extension_counts


def scan_all_extensions(
    root_dir: Path = Path("."),
    ignore_patterns: list[str] | None = None,
    use_standard_filters: bool = True,
) -> list[str]:
    """Scan directory for all file extensions and return them sorted by occurrence count.

    Args:
        root_dir: Root directory to scan
        ignore_patterns: List of patterns to ignore
        use_standard_filters: If True, also filter out files in STANDARD_DIRECTORY_NAMES
            and files matching STANDARD_FILE_NAME_PREFIXES/STANDARD_FILE_NAMES

    Returns list of extensions with dots (e.g., [".svelte", ".ts", ".py"]),
    sorted by occurrence count (descending), then alphabetically.
    """
    if ignore_patterns is None:
        ignore_patterns = DEFAULT_IGNORE_PATTERNS.copy()
    else:
        ignore_patterns = ignore_patterns.copy()

    # Load .gitignore patterns (cached)
    gitignore_patterns = _load_gitignore_patterns(root_dir)
    ignore_patterns.extend(gitignore_patterns)

    # Import standard filters if needed
    if use_standard_filters:
        from src.config import (
            STANDARD_DIRECTORY_NAMES,
            STANDARD_FILE_NAME_PREFIXES,
            STANDARD_FILE_NAMES,
        )
    else:
        STANDARD_DIRECTORY_NAMES = []
        STANDARD_FILE_NAME_PREFIXES = []
        STANDARD_FILE_NAMES = []

    extension_counts: dict[str, int] = {}

    for root, dirs, filenames in os.walk(root_dir):
        # Filter out ignored directories
        dirs[:] = [
            d for d in dirs if not should_ignore(Path(root) / d, ignore_patterns)
        ]

        # Also filter out standard directories if use_standard_filters is enabled
        if use_standard_filters:
            dirs[:] = [d for d in dirs if d not in STANDARD_DIRECTORY_NAMES]

        for filename in filenames:
            file_path = Path(root) / filename
            if should_ignore(file_path, ignore_patterns):
                continue

            # Apply standard filters if enabled
            if use_standard_filters:
                file_name = file_path.name
                should_ignore_file = False

                # Check standard prefixes (e.g., ".", "__")
                for prefix in STANDARD_FILE_NAME_PREFIXES:
                    if file_name.startswith(prefix):
                        should_ignore_file = True
                        break

                # Check standard file names (exact matches)
                if not should_ignore_file and file_name in STANDARD_FILE_NAMES:
                    should_ignore_file = True

                # Check if file is in a standard directory
                if not should_ignore_file:
                    # Check if any parent directory matches standard directory names
                    for parent in file_path.parents:
                        if parent.name in STANDARD_DIRECTORY_NAMES:
                            should_ignore_file = True
                            break

                if should_ignore_file:
                    continue

            # Get extension (with dot)
            ext = file_path.suffix
            # Only count files with extensions (skip files without extensions)
            if ext:
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

    # Sort by count (descending), then alphabetically
    sorted_extensions = sorted(
        extension_counts.items(),
        key=lambda x: (-x[1], x[0]),  # Negative count for descending order
    )

    # Return just the extension strings
    return [ext for ext, _ in sorted_extensions]
