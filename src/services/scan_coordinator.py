"""Scan coordinator service for managing file scanning workflow."""

from pathlib import Path

from src.config import MAX_FILES_HARD_LIMIT, MAX_FILES_WARNING


class ScanCoordinator:
    """Service for coordinating file scanning operations and caching extension counts."""

    def __init__(self):
        self._cached_extension_counts: dict[str, dict[str, int]] = {}

    def get_cached_extension_counts(self, directory: Path) -> dict[str, int] | None:
        """Get cached extension counts for a directory.

        Args:
            directory: Directory path

        Returns:
            Extension counts dictionary or None if not cached
        """
        dir_key = str(directory.resolve())
        return self._cached_extension_counts.get(dir_key)

    def cache_extension_counts(
        self, directory: Path, extension_counts: dict[str, int]
    ) -> None:
        """Cache extension counts for a directory.

        Args:
            directory: Directory path
            extension_counts: Dictionary mapping extensions to counts
        """
        dir_key = str(directory.resolve())
        if extension_counts:
            self._cached_extension_counts[dir_key] = extension_counts

    def should_collect_extensions(self, directory: Path) -> bool:
        """Check if extension collection should be performed (not cached).

        Args:
            directory: Directory path

        Returns:
            True if extensions should be collected, False if cached
        """
        return self.get_cached_extension_counts(directory) is None

    def clear_extension_cache(self, directory: Path) -> None:
        """Clear cached extension counts for a directory.

        Args:
            directory: Directory path
        """
        dir_key = str(directory.resolve())
        self._cached_extension_counts.pop(dir_key, None)

    def validate_file_count(
        self, file_count: int, extension: str
    ) -> tuple[bool, str | None]:
        """Validate file count and determine if scan should proceed.

        Args:
            file_count: Number of files found
            extension: File extension being scanned

        Returns:
            Tuple of (should_proceed, warning_message)
            - should_proceed: True if scan should continue, False if should stop
            - warning_message: Warning message if count is high, None otherwise
        """
        if file_count > MAX_FILES_HARD_LIMIT:
            return (
                False,
                f"This directory contains more than {MAX_FILES_HARD_LIMIT:,} {extension} files.\n\nScanning this many files may cause the application to freeze or crash.\n\nPlease select a more specific directory or use a different file extension.",
            )

        if file_count > MAX_FILES_WARNING:
            return (
                True,
                f"This directory contains {file_count:,} {extension} files.\n\nScanning this many files may take a while and could cause performance issues.\n\nDo you want to continue?",
            )

        return True, None

    def should_show_warning(self, file_count: int) -> bool:
        """Check if file count warning should be shown.

        Args:
            file_count: Number of files found

        Returns:
            True if warning should be shown
        """
        return file_count > MAX_FILES_WARNING

    def is_hard_limit_exceeded(self, file_count: int) -> bool:
        """Check if hard limit is exceeded.

        Args:
            file_count: Number of files found

        Returns:
            True if hard limit is exceeded
        """
        return file_count > MAX_FILES_HARD_LIMIT
