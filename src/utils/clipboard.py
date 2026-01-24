"""Clipboard operations."""
import pyperclip
from typing import Callable

from src.utils.tokens import format_token_info


def copy_to_clipboard(text: str, on_success: Callable[[str], None] | None = None) -> bool:
    """Copy text to clipboard and optionally call success callback. Returns True on success, False on failure."""
    try:
        pyperclip.copy(text)
        if on_success:
            token_info = format_token_info(text)
            on_success(f"Copied {token_info} to clipboard")
        return True
    except Exception as e:
        if on_success:
            on_success(f"Failed to copy to clipboard: {e}")
        return False

