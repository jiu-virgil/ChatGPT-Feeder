"""Content formatting and minification utilities."""

from pathlib import Path
from typing import Final


def minify_content(content: str) -> str:
    """Lightweight minification: remove trailing whitespace and collapse excessive blank lines.

    Preserves code structure, comments, and indentation for LLM readability.
    """
    if not content:
        return content

    lines = content.splitlines()
    minified_lines = []
    blank_line_count = 0

    for line in lines:
        # Remove trailing whitespace
        stripped = line.rstrip()

        # Check if line is blank (empty after stripping)
        if not stripped:
            blank_line_count += 1
            # Collapse 3+ consecutive blank lines to max 2 blank lines
            if blank_line_count <= 2:
                minified_lines.append("")
        else:
            blank_line_count = 0
            minified_lines.append(stripped)

    # Join with newlines and remove leading/trailing whitespace
    result = "\n".join(minified_lines)
    return result.strip()


def generate_file_structure(file_paths: list[str]) -> str:
    """Generate a tree structure representation from file paths.

    Args:
        file_paths: List of file path strings

    Returns:
        Formatted tree structure as string
    """
    if not file_paths:
        return ""

    # Build directory tree structure
    tree = {}
    for file_path_str in file_paths:
        path = Path(file_path_str)
        parts = path.parts

        # Navigate/create tree structure
        current = tree
        for part in parts[:-1]:  # All parts except filename
            if part not in current:
                current[part] = {}
            current = current[part]

        # Add file to current directory
        filename = parts[-1]
        if "__files__" not in current:
            current["__files__"] = []
        current["__files__"].append(filename)

    def format_tree(node: dict, prefix: str = "", is_last: bool = True) -> list[str]:
        """Recursively format tree structure with proper indentation."""
        lines = []
        items = [(k, v) for k, v in node.items() if k != "__files__"]
        files = node.get("__files__", [])
        all_items = items + [("__files__", files)] if files else items

        for i, (key, value) in enumerate(all_items):
            is_last_item = i == len(all_items) - 1
            connector = "└── " if is_last_item else "├── "

            if key == "__files__":
                # Format files
                for j, filename in enumerate(value):
                    is_last_file = j == len(value) - 1
                    file_connector = "└── " if is_last_file else "├── "
                    file_prefix = prefix + ("    " if is_last else "│   ")
                    lines.append(f"{file_prefix}{file_connector}{filename}")
            else:
                # Format directory
                lines.append(f"{prefix}{connector}{key}/")
                next_prefix = prefix + ("    " if is_last_item else "│   ")
                lines.extend(format_tree(value, next_prefix, is_last_item))

        return lines

    # Generate tree lines
    tree_lines = format_tree(tree)

    # Format as comment block
    structure = "# File Structure\n"
    if tree_lines:
        structure += "\n".join(tree_lines)
    else:
        structure += "  (no files)"

    return structure


def format_files_for_llm(
    content_map: dict[str, str], minify: bool = True, include_structure: bool = True
) -> str:
    """Format file contents for LLMs with file path headers.

    Args:
        content_map: Dictionary mapping file paths to their contents
        minify: Whether to minify the content (default: True)
        include_structure: Whether to include file structure overview at the top (default: True)

    Returns:
        Formatted string with file contents, optionally prefixed with file structure
    """
    # Generate file structure if requested
    structure = ""
    if include_structure and content_map:
        structure = generate_file_structure(list(content_map.keys()))
        structure += "\n\n"

    # Format file contents
    formatted = []
    for file_path, content in content_map.items():
        processed_content = minify_content(content) if minify else content
        formatted.append(f"# {file_path}\n{processed_content}")

    file_contents = "\n\n".join(formatted)

    # Combine structure and contents
    return structure + file_contents
