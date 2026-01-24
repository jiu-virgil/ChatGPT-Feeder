"""File service for coordinating file operations and caching."""

from pathlib import Path

from src.utils.content_formatter import format_files_for_llm
from src.utils.file_reader import collect_files_content, read_file_content


class FileService:
    """Service for coordinating file reading operations with caching."""

    def __init__(self):
        self._content_cache: dict[str, str] = {}

    def get_file_content(self, file_path: Path | str, use_cache: bool = True) -> str:
        """Get file content, using cache if available.

        Args:
            file_path: Path to the file
            use_cache: Whether to use cache (default: True)

        Returns:
            File content as string
        """
        path_str = str(file_path)

        if use_cache and path_str in self._content_cache:
            return self._content_cache[path_str]

        content = read_file_content(file_path)

        if use_cache:
            self._content_cache[path_str] = content

        return content

    def get_files_content(
        self, file_paths: list[Path | str], use_cache: bool = True
    ) -> dict[str, str]:
        """Get content from multiple files, using cache when available.

        Args:
            file_paths: List of file paths
            use_cache: Whether to use cache (default: True)

        Returns:
            Dictionary mapping file paths to their contents
        """
        content_map = {}

        for file_path in file_paths:
            path_str = str(file_path)
            path = Path(file_path)

            if path.exists() and path.is_file():
                if use_cache and path_str in self._content_cache:
                    content_map[path_str] = self._content_cache[path_str]
                else:
                    content = read_file_content(path)
                    content_map[path_str] = content
                    if use_cache:
                        self._content_cache[path_str] = content

        return content_map

    def format_files_for_llm(
        self,
        file_paths: list[Path | str],
        minify: bool = True,
        use_cache: bool = True,
        include_structure: bool = True,
    ) -> str:
        """Format file contents for LLMs.

        Args:
            file_paths: List of file paths
            minify: Whether to minify content (default: True)
            use_cache: Whether to use cache (default: True)
            include_structure: Whether to include file structure overview (default: True)

        Returns:
            Formatted string with file contents, optionally with file structure
        """
        content_map = self.get_files_content(file_paths, use_cache=use_cache)
        return format_files_for_llm(
            content_map, minify=minify, include_structure=include_structure
        )

    def clear_cache(self) -> None:
        """Clear the file content cache."""
        self._content_cache.clear()

    def get_cache(self) -> dict[str, str]:
        """Get the file content cache (for use with workers).

        Returns:
            Reference to the cache dictionary
        """
        return self._content_cache
