"""File extension utilities and normalization."""

from typing import Final

DEFAULT_EXTENSION: Final[str] = ".py"


def normalize_extension(ext: str, default: str = DEFAULT_EXTENSION) -> str:
    """Normalize extension to always start with a dot.

    Args:
        ext: Extension string (with or without dot)
        default: Default extension to use if ext is empty

    Returns:
        Normalized extension string (always starts with dot)
    """
    ext = ext.strip()
    if not ext:
        return default
    # Add dot if missing
    if not ext.startswith("."):
        ext = "." + ext
    return ext


def parse_extension_from_text(text: str, default: str = DEFAULT_EXTENSION) -> str:
    """Parse extension from display text, removing warnings and counts.

    Args:
        text: Display text that may contain warnings/emojis and counts
              (e.g., ".svg ⚠️ (2000)" or ".py (100)")
        default: Default extension to use if parsing fails

    Returns:
        Normalized extension string (or comma-separated string for multiple extensions)
    """
    text = text.strip()
    # Remove warning emoji and count if present (e.g., ".svg ⚠️ (2000)" -> ".svg")
    if " ⚠️ " in text:
        text = text.split(" ⚠️ ")[0]
    elif " (" in text:
        text = text.split(" (")[0]

    # Check if it contains commas (multiple extensions)
    if "," in text:
        # Parse comma-separated extensions
        extensions = [
            normalize_extension(ext.strip(), default)
            for ext in text.split(",")
            if ext.strip()
        ]
        return (
            ",".join(extensions) if extensions else normalize_extension(text, default)
        )

    return normalize_extension(text, default)


def parse_extensions(extension_str: str) -> list[str]:
    """Parse extension string into a list of normalized extensions.

    Args:
        extension_str: Extension string (single or comma-separated)
                     Empty string means "any" (all extensions)

    Returns:
        List of normalized extension strings, or empty list for "any"
    """
    if not extension_str or extension_str.strip() == "":
        return []  # Empty list means "any"

    # Check if it contains commas
    if "," in extension_str:
        extensions = [
            normalize_extension(ext.strip())
            for ext in extension_str.split(",")
            if ext.strip()
        ]
        return extensions

    # Single extension
    return [normalize_extension(extension_str)]


def matches_extension(file_suffix: str, extension_str: str) -> bool:
    """Check if a file suffix matches the extension string.

    Args:
        file_suffix: File suffix (e.g., ".py", ".ts")
        extension_str: Extension string (single or comma-separated, empty means "any")

    Returns:
        True if file matches the extension(s), False otherwise
    """
    if not extension_str or extension_str.strip() == "":
        return True  # Empty means "any" - match all

    # Parse extensions
    extensions = parse_extensions(extension_str)
    if not extensions:
        return True  # Empty list means "any"

    # Check if file suffix matches any of the extensions
    return file_suffix in extensions
