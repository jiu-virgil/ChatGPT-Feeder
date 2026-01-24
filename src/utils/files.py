"""File utilities - DEPRECATED: Use file_scanner, file_reader, or content_formatter instead.

This module is kept for backward compatibility but will be removed in a future version.
Please update imports to use the specific modules:
- file_scanner: scanning operations
- file_reader: reading operations
- content_formatter: formatting operations
"""
from src.utils.file_scanner import (
    count_files,
    scan_files,
    scan_all_extensions,
    should_ignore,
)
from src.utils.file_reader import (
    read_file_content,
    collect_files_content,
    open_file_in_editor,
)
from src.utils.content_formatter import (
    minify_content,
    format_files_for_llm,
)

__all__ = [
    "count_files",
    "scan_files",
    "scan_all_extensions",
    "should_ignore",
    "read_file_content",
    "collect_files_content",
    "open_file_in_editor",
    "minify_content",
    "format_files_for_llm",
]
