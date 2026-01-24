"""Tree status indicator widget."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QWidget

from src.utils.icons import get_ui_icon


class TreeStatusWidget(QWidget):
    """Widget displaying the current tree load status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._setup_ui()
        self._set_status("idle", "")

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Status icon and text
        self._status_label = QLabel()
        self._status_label.setStyleSheet("font-size: 9pt; padding: 4px 8px;")
        self._status_label.setWordWrap(True)  # Enable text wrapping
        self._status_label.setAlignment(
            Qt.AlignLeft | Qt.AlignTop
        )  # Align text to top-left
        layout.addWidget(self._status_label)

        layout.addStretch()
        self.setLayout(layout)

    def _set_status(self, status: str, message: str) -> None:
        """Set the status display."""
        if status == "loading":
            text = "Loading..."
            color = "palette(window-text)"
        elif status == "loaded":
            text = message
            color = "#4caf50"  # Green
        elif status == "empty":
            text = f"No files found: {message}"
            color = "#ff9800"  # Orange
        elif status == "error":
            text = f"Error: {message}"
            color = "#f44336"  # Red
        else:  # idle
            text = "Ready to load directory"
            color = "palette(window-text)"

        self._status_label.setText(text)
        self._status_label.setStyleSheet(
            f"font-size: 9pt; padding: 4px 8px; color: {color}; font-weight: 500;"
        )

    def set_loading(self) -> None:
        """Set status to loading."""
        self._set_status("loading", "")

    def set_loaded(
        self,
        file_count: int,
        extension: str,
        tokens: int,
        line_count: int,
        percentages: dict[str, float] | None = None,
    ) -> None:
        """Set status to loaded with file count, tokens, and line count."""
        if file_count == 0:
            self.set_empty(extension)
        else:
            message = f"{file_count} {extension} file{'s' if file_count != 1 else ''}, {tokens:,} tokens, {line_count:,} lines"
            # Append percentages if provided
            if percentages:
                from src.utils.tokens import format_percentage

                pct_str = ", ".join(
                    [
                        f"{name}: {format_percentage(pct)}"
                        for name, pct in percentages.items()
                    ]
                )
                message = f"{message} - {pct_str}"
            self._set_status("loaded", message)

    def set_empty(self, extension: str) -> None:
        """Set status to empty (no files found)."""
        message = f"No {extension} files in directory"
        self._set_status("empty", message)

    def set_error(self, error_message: str) -> None:
        """Set status to error."""
        self._set_status("error", error_message)

    def set_idle(self) -> None:
        """Set status to idle."""
        self._set_status("idle", "")
