"""Toolbar component with extension filter and actions."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.utils.extensions import (
    normalize_extension,
    parse_extension_from_text,
    parse_extensions,
)
from src.utils.icons import get_icon_for_extension, get_ui_icon
from src.utils.paths import shorten_home_path
from src.utils.ui_helpers import update_dropdown_arrow_visibility
from src.workers import ExtensionScannerWorker


class ExtensionFilter(QWidget):
    """File extension filter widget with dropdown of available extensions."""

    extension_changed = Signal(str)
    extensions_updated = Signal()  # Emitted when extension list is updated

    def __init__(self, default_extension: str = ".py", parent=None):
        super().__init__(parent)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ComboBox for extension selection/input
        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.setFixedWidth(
            120
        )  # Increased width to accommodate comma-separated extensions
        self._combo.setToolTip(
            "Select file extension from dropdown or type custom extension (e.g., .svelte, .ts for multiple)"
        )
        self._combo.lineEdit().returnPressed.connect(self._on_enter)
        self._combo.lineEdit().textChanged.connect(self._on_text_changed)
        self._combo.lineEdit().editingFinished.connect(self._on_editing_finished)
        self._combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self._combo)

        # Track if we're updating programmatically to avoid false signals
        self._updating = False

        # Worker thread for async extension scanning
        self._scanner_worker: ExtensionScannerWorker | None = None

        # Track pending icon updates to prevent crashes
        self._icon_update_timer = None

        self.setLayout(layout)

        # Set initial extension
        self.set_extension(default_extension)

    def _find_and_select_extension(self, extension: str) -> int:
        """Find extension in combo box and select it, adding if necessary.

        Args:
            extension: Normalized extension string

        Returns:
            Index of the selected item, or -1 if not found/added
        """
        # Try to find by data first
        index = self._combo.findData(extension)
        if index < 0:
            # Try to find by text
            index = self._combo.findText(extension)

        if index < 0:
            # Extension not found, add it
            self._add_extension_with_icon(extension)
            # Find the newly added item
            index = self._combo.findData(extension)
            if index < 0:
                index = self._combo.findText(extension)

        if index >= 0:
            self._combo.setCurrentIndex(index)

        return index

    def _add_extension_with_icon(self, extension: str) -> None:
        """Add extension to combo box with icon, handling errors gracefully.

        Args:
            extension: Normalized extension string
        """
        try:
            icon = get_icon_for_extension(extension)
            self._combo.addItem(icon, extension)
        except Exception as e:
            # If icon loading fails, add item without icon
            print(f"Warning: Failed to load icon for extension {extension}: {e}")
            self._combo.addItem(extension)

    def _on_enter(self) -> None:
        """Handle Enter key press - emit extension change."""
        if self._updating:
            return
        # Get currently selected extension (from item data, not text)
        current_index = self._combo.currentIndex()
        current_selected_ext = ""
        if current_index >= 0:
            ext_data = self._combo.itemData(current_index)
            if isinstance(ext_data, str):
                current_selected_ext = ext_data

        # Get extension from text input
        text_ext = self.get_extension()
        normalized = normalize_extension(text_ext)

        # Only emit if extension actually changed from what's currently selected
        if normalized != current_selected_ext:
            self._find_and_select_extension(normalized)
            self.extension_changed.emit(normalized)
        # If unchanged, don't emit (avoids unnecessary scans)

    def _on_text_changed(self, _text: str) -> None:
        """Handle text change when user types in the combobox."""
        if self._updating:
            return
        # Don't emit on every keystroke - wait for Enter, selection, or focus out
        pass

    def _on_editing_finished(self) -> None:
        """Handle when user finishes editing (clicks away or tabs out)."""
        if self._updating:
            return
        # Get currently selected extension (from item data, not text)
        current_index = self._combo.currentIndex()
        current_selected_ext = ""
        if current_index >= 0:
            ext_data = self._combo.itemData(current_index)
            if isinstance(ext_data, str):
                current_selected_ext = ext_data

        # Get extension from text input
        text_ext = self.get_extension()
        normalized = normalize_extension(text_ext)

        # Only emit if extension actually changed from what's currently selected
        if normalized != current_selected_ext:
            self._find_and_select_extension(normalized)
            self.extension_changed.emit(normalized)
        # If unchanged, don't emit (avoids unnecessary scans on focus loss)

    def _on_selection_changed(self, index: int) -> None:
        """Handle selection change from dropdown."""
        if self._updating:
            return
        # Emit when dropdown item is selected (index >= 0 means item selected, not typed)
        if index >= 0:
            normalized = normalize_extension(self.get_extension())
            self.extension_changed.emit(normalized)

    def get_extension(self) -> str:
        """Get current extension, normalized (always starts with dot).

        Supports comma-separated extensions (e.g., ".svelte, .ts").

        Returns empty string "" for "any" option.
        """
        # First try to get extension from item data (if set by _update_extensions_from_list)
        current_index = self._combo.currentIndex()
        if current_index >= 0:
            extension_data = self._combo.itemData(current_index)
            # Check isinstance first to handle empty string correctly
            if isinstance(extension_data, str):
                # Empty string represents "any" - return as-is
                if extension_data == "":
                    return ""
                # Check if it's already comma-separated
                if "," in extension_data:
                    return extension_data
                return normalize_extension(extension_data)

        # Fallback: parse from display text (remove warning and count)
        text = self._combo.currentText().strip()
        # Check if it's "any"
        if text.lower() == "any":
            return ""
        return parse_extension_from_text(text)

    def set_extension(self, extension: str) -> None:
        """Set extension value programmatically."""
        # Handle empty string (any) specially - don't normalize it
        if extension == "":
            normalized = ""
        else:
            normalized = normalize_extension(extension)
        # Block signals to avoid triggering change
        self._updating = True
        self._combo.blockSignals(True)
        self._find_and_select_extension(normalized)
        self._combo.blockSignals(False)
        self._updating = False

    def update_available_extensions(
        self,
        directory: Path,
        set_to_most_common: bool = False,
        use_standard_filters: bool = True,
    ) -> None:
        """Update dropdown with available extensions from directory.

        Args:
            directory: Directory to scan for extensions
            set_to_most_common: If True, always set to most common (first in list).
                              If False, preserve current extension only if it exists in the list,
                              otherwise set to most common.
            use_standard_filters: If True, respect standard directory filters when scanning.
        """
        # Store parameters for use in callback
        self._pending_set_to_most_common = set_to_most_common
        self._pending_current_ext = self.get_extension()

        # Cancel/cleanup any existing worker
        self._cleanup_worker()

        # Create and start new worker thread
        self._scanner_worker = ExtensionScannerWorker(
            directory, use_standard_filters=use_standard_filters
        )
        self._scanner_worker.finished.connect(self._on_scan_finished)
        self._scanner_worker.start()

    def _update_extensions_from_list(self, extension_counts: dict[str, int]) -> None:
        """Update extension dropdown from extension counts dict (internal method).

        This is used when extensions are collected during file scanning to avoid
        a separate directory scan.

        Args:
            extension_counts: Dict mapping extension (with dot) to file count
        """
        set_to_most_common = getattr(self, "_pending_set_to_most_common", False)
        current_ext = getattr(self, "_pending_current_ext", self.get_extension())

        # Block signals during update
        self._updating = True
        self._combo.blockSignals(True)
        self._combo.clear()

        # Add "any" option as first item (shows all files regardless of extension)
        self._combo.addItem("any")
        # Get index after adding (addItem returns None in PySide6)
        any_index = self._combo.count() - 1
        self._combo.setItemData(any_index, "")  # Empty string represents "any"
        self._combo.setItemData(
            any_index, "Show all files regardless of extension", Qt.ToolTipRole
        )

        if extension_counts:
            # Sort extensions by count (descending), then alphabetically
            sorted_extensions = sorted(
                extension_counts.items(),
                key=lambda x: (-x[1], x[0]),  # Negative count for descending order
            )

            # Add items to dropdown with warnings for high-count extensions
            extensions_list = []
            for ext, count in sorted_extensions:
                # Format display text with warning if count > 100
                if count > 100:
                    display_text = f"{ext} ({count:,}) ⚠"
                    tooltip = f"{ext} - {count:,} files (warning: over 100 files may cause performance issues)"
                else:
                    display_text = f"{ext} ({count:,})"
                    tooltip = f"{ext} - {count:,} files"

                # Store extension as data, display text as shown text
                self._combo.addItem(display_text)
                # Get index after adding (addItem returns None in PySide6)
                index = self._combo.count() - 1
                self._combo.setItemData(index, ext)  # Store actual extension as data
                self._combo.setItemData(index, tooltip, Qt.ToolTipRole)

                extensions_list.append(ext)

            # Determine which extension to use
            # If current extension is empty string (any), select index 0
            if current_ext == "":
                self._combo.setCurrentIndex(0)
            else:
                default_index = self._select_best_default_extension(
                    extension_counts, current_ext, set_to_most_common
                )

                if set_to_most_common:
                    # Use best available default (prefer lower counts)
                    self._combo.setCurrentIndex(default_index)
                elif current_ext in extension_counts:
                    # Preserve current extension if it exists
                    index = self._combo.findData(current_ext)
                    if index >= 0:
                        self._combo.setCurrentIndex(index)
                    else:
                        # Fallback to best default
                        self._combo.setCurrentIndex(default_index)
                else:
                    # Current extension not in list, use best default
                    self._combo.setCurrentIndex(default_index)

            # Update icons asynchronously
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, lambda: self._update_extension_icons(extensions_list))
        else:
            # No extensions found
            # If current extension is empty string (any), it's already at index 0
            if current_ext != "":
                # Keep current extension with icon (add after "any")
                self._add_extension_with_icon(current_ext)
                self._combo.setCurrentIndex(1)
            else:
                # "any" is already selected at index 0
                pass

        self._combo.blockSignals(False)
        self._updating = False

        # Update dropdown arrow visibility
        self._update_dropdown_arrow_visibility()

        # Emit signal that extensions list has been updated
        self.extensions_updated.emit()

    def _select_best_default_extension(
        self,
        extension_counts: dict[str, int],
        _current_ext: str,
        _set_to_most_common: bool,
    ) -> int:
        """Select the best default extension based on counts and preferences.

        Args:
            extension_counts: Dictionary mapping extensions to counts
            current_ext: Current extension to preserve if possible
            set_to_most_common: Whether to always use most common

        Returns:
            Index of the selected extension in combo box
        """
        # Find the best default extension:
        # 1. First preference: count <= 100
        # 2. Second preference: count <= 1000 (reasonable limit)
        # 3. Last resort: lowest count overall (to avoid very high counts like 2000+)
        best_index_100 = -1
        best_index_1000 = -1
        lowest_count_index = -1
        lowest_count = float("inf")

        # Iterate through combo box items to find indices
        # Skip index 0 which is "any" (empty string)
        for idx in range(1, self._combo.count()):
            ext = self._combo.itemData(idx)
            if not ext or not isinstance(ext, str):
                continue

            count = extension_counts.get(ext, 0)

            # Track best options for default selection
            if best_index_100 < 0 and count <= 100:
                best_index_100 = idx
            elif best_index_1000 < 0 and count <= 1000:
                best_index_1000 = idx

            # Track lowest count overall (for last resort)
            if count < lowest_count:
                lowest_count = count
                lowest_count_index = idx

        # Determine which extension to use
        # Priority: best_100 > best_1000 > lowest_count > first extension (index 1) > "any" (index 0)
        # If we have extensions, prefer first extension over "any"
        fallback_index = 1 if self._combo.count() > 1 else 0
        default_index = (
            best_index_100
            if best_index_100 >= 0
            else (
                best_index_1000
                if best_index_1000 >= 0
                else (lowest_count_index if lowest_count_index >= 0 else fallback_index)
            )
        )

        return default_index

    def _on_scan_finished(self, extensions: list[str]) -> None:
        """Handle completion of async extension scan."""
        set_to_most_common = getattr(self, "_pending_set_to_most_common", False)
        current_ext = getattr(self, "_pending_current_ext", self.get_extension())

        # Block signals during update
        self._updating = True
        self._combo.blockSignals(True)
        self._combo.clear()

        # Add "any" option as first item (shows all files regardless of extension)
        self._combo.addItem("any")
        # Get index after adding (addItem returns None in PySide6)
        any_index = self._combo.count() - 1
        self._combo.setItemData(any_index, "")  # Empty string represents "any"
        self._combo.setItemData(
            any_index, "Show all files regardless of extension", Qt.ToolTipRole
        )

        if extensions:
            # Add items WITHOUT icons first (fast, non-blocking)
            # Icons will be loaded lazily or updated later to avoid UI freeze
            for ext in extensions:
                self._combo.addItem(ext)

            # Determine which extension to use
            # If current extension is empty string (any), select index 0
            if current_ext == "":
                self._combo.setCurrentIndex(0)
            elif set_to_most_common:
                # Always set to most common (first extension after "any", so index 1)
                self._combo.setCurrentIndex(1 if len(extensions) > 0 else 0)
            elif current_ext in extensions:
                # Preserve current extension if it exists in the list
                index = self._combo.findText(current_ext)
                if index >= 0:
                    self._combo.setCurrentIndex(index)
                else:
                    # Fallback to most common (index 1)
                    self._combo.setCurrentIndex(1 if len(extensions) > 0 else 0)
            else:
                # Current extension not in list, use most common (index 1)
                self._combo.setCurrentIndex(1 if len(extensions) > 0 else 0)

            # Update icons asynchronously after UI is responsive
            # Use QTimer.singleShot to yield to event loop, then update icons
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, lambda: self._update_extension_icons(extensions))
        else:
            # No extensions found
            # If current extension is empty string (any), it's already at index 0
            if current_ext != "":
                # Keep current extension with icon (add after "any")
                self._add_extension_with_icon(current_ext)
                self._combo.setCurrentIndex(1)
            else:
                # "any" is already selected at index 0
                pass

        self._combo.blockSignals(False)
        self._updating = False

        # Update dropdown arrow visibility
        self._update_dropdown_arrow_visibility()

        # Emit signal that extensions list has been updated
        self.extensions_updated.emit()

    def _update_extension_icons(self, extensions: list[str]) -> None:
        """Update icons for extension items asynchronously."""
        if not extensions:
            return

        # Cancel any existing icon update timer
        if self._icon_update_timer:
            self._icon_update_timer.stop()

        # Update icons one at a time, yielding to event loop between each
        from PySide6.QtCore import QTimer

        current_index = [0]  # Use list to allow modification in closure

        def update_next_icon():
            # Check if combo box still exists and has items
            if (
                not self._combo
                or current_index[0] >= len(extensions)
                or current_index[0] >= self._combo.count()
            ):
                self._icon_update_timer = None
                return

            ext = extensions[current_index[0]]
            try:
                # Try to find by data first (for items added via _update_extensions_from_list)
                combo_index = self._combo.findData(ext)
                if combo_index < 0:
                    # Fallback to findText for backwards compatibility
                    combo_index = self._combo.findText(ext)
                if combo_index >= 0:
                    icon = get_icon_for_extension(ext)
                    if not icon.isNull():
                        self._combo.setItemIcon(combo_index, icon)
            except Exception:
                # Silently fail - icon update is not critical
                pass

            # Schedule next icon update
            current_index[0] += 1
            if current_index[0] < len(extensions):
                self._icon_update_timer = QTimer()
                self._icon_update_timer.setSingleShot(True)
                self._icon_update_timer.timeout.connect(update_next_icon)
                self._icon_update_timer.start(10)
            else:
                self._icon_update_timer = None

        # Start updating icons
        self._icon_update_timer = QTimer()
        self._icon_update_timer.setSingleShot(True)
        self._icon_update_timer.timeout.connect(update_next_icon)
        self._icon_update_timer.start(10)

    def _update_dropdown_arrow_visibility(self) -> None:
        """Show or hide the dropdown arrow based on whether there are items."""
        update_dropdown_arrow_visibility(self._combo)

    def _cleanup_worker(self) -> None:
        """Clean up worker thread if it's running."""
        if self._scanner_worker and self._scanner_worker.isRunning():
            self._scanner_worker.terminate()
            self._scanner_worker.wait()
            self._scanner_worker = None

        # Cancel any pending icon updates
        if self._icon_update_timer:
            self._icon_update_timer.stop()
            self._icon_update_timer = None


class Toolbar(QWidget):
    """Main toolbar with actions."""

    expand_all_clicked = Signal()
    collapse_all_clicked = Signal()
    search_changed = Signal(str)
    path_changed = Signal(str)
    ignore_pattern_changed = Signal(str, bool)  # pattern, enabled

    def __init__(self, default_extension: str = ".py", parent=None):
        super().__init__(parent)

        # Two-row layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Row 1: Path input and extension filter
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        # Browse button (icon only) - moved before path input
        folder_icon = get_ui_icon("folder-open")
        self._browse_btn = QPushButton()
        if not folder_icon.isNull():
            self._browse_btn.setIcon(folder_icon)
        else:
            self._browse_btn.setText("📂")  # Fallback to emoji if icon not found
        self._browse_btn.setToolTip("Browse for directory")
        self._browse_btn.clicked.connect(self._on_browse_clicked)
        self._browse_btn.setFixedSize(
            32, 32
        )  # Make it square/compact for icon-only button
        row1.addWidget(self._browse_btn)

        # Path input with recent directories dropdown
        self._path_input = QComboBox()
        self._path_input.setEditable(True)
        self._path_input.setFixedHeight(32)  # Match folder button height
        self._path_input.setToolTip(
            "Enter directory path or select from recent directories"
        )
        self._path_input.lineEdit().returnPressed.connect(self._on_path_entered)
        self._path_input.currentIndexChanged.connect(self._on_path_selected)
        # Use activated signal for more reliable user selection detection (only fires on explicit user selection)
        self._path_input.activated.connect(self._on_path_selected)
        row1.addWidget(self._path_input, 1)  # Stretch factor 1 to make it expand

        # Modern separator with subtle styling
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setFrameShadow(QFrame.Plain)
        sep1.setStyleSheet(
            """
            QFrame {
                border: none;
                border-left: 1px solid palette(mid);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 transparent, stop:0.5 palette(mid), stop:1 transparent);
                max-width: 1px;
            }
        """
        )
        row1.addWidget(sep1)

        # Minify checkbox
        self._minify_checkbox = QCheckBox("Minify")
        self._minify_checkbox.setChecked(True)  # Enabled by default
        self._minify_checkbox.setToolTip(
            "Minify code by removing trailing whitespace and collapsing excessive blank lines"
        )
        row1.addWidget(self._minify_checkbox)

        main_layout.addLayout(row1)

        # Row 2: Extension filter and ignore pattern (swapped with row 3)
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        # Extension filter with label
        ext_label = QLabel("Extension:")
        ext_label.setStyleSheet("padding-right: 4px;")
        row2.addWidget(ext_label)
        self.extension_filter = ExtensionFilter(default_extension)
        row2.addWidget(self.extension_filter)

        # Ignore pattern filter
        ignore_label = QLabel("Ignore prefix:")
        ignore_label.setStyleSheet("padding-right: 4px;")
        row2.addWidget(ignore_label)
        self._ignore_pattern_input = QLineEdit()
        self._ignore_pattern_input.setPlaceholderText("e.g., __ or .")
        self._ignore_pattern_input.setMinimumWidth(80)
        self._ignore_pattern_input.setMaximumWidth(120)
        self._ignore_pattern_input.textChanged.connect(self._on_ignore_pattern_changed)
        row2.addWidget(self._ignore_pattern_input)

        # Use Standard Filters checkbox
        self._standard_filters_checkbox = QCheckBox("Use Standard Filters")
        self._standard_filters_checkbox.setChecked(True)  # Enabled by default
        self._standard_filters_checkbox.setToolTip(
            "When checked, uses standard file filtering. When unchecked, applies custom ignore prefix pattern."
        )
        self._standard_filters_checkbox.stateChanged.connect(
            self._on_ignore_pattern_changed
        )
        row2.addWidget(self._standard_filters_checkbox)

        main_layout.addLayout(row2)

        # Row 3: Expand/collapse and search (swapped with row 2)
        row3 = QHBoxLayout()
        row3.setSpacing(8)

        # Action buttons with icons
        expand_icon = get_ui_icon("expand")
        self._expand_btn = QPushButton("Expand All")
        if not expand_icon.isNull():
            self._expand_btn.setIcon(expand_icon)
        self._expand_btn.setToolTip("Expand all tree items")
        self._expand_btn.clicked.connect(self.expand_all_clicked.emit)
        row3.addWidget(self._expand_btn)

        collapse_icon = get_ui_icon("collapse")
        self._collapse_btn = QPushButton("Collapse All")
        if not collapse_icon.isNull():
            self._collapse_btn.setIcon(collapse_icon)
        self._collapse_btn.setToolTip("Collapse all tree items")
        self._collapse_btn.clicked.connect(self.collapse_all_clicked.emit)
        row3.addWidget(self._collapse_btn)

        # Search filter - label tied to input, not buttons
        search_label = QLabel("Search:")
        search_label.setStyleSheet("padding-right: 4px;")
        row3.addWidget(search_label)
        # Search input
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filter files...")
        self._search_input.setMinimumWidth(120)
        self._search_input.setMaximumWidth(200)
        self._search_input.textChanged.connect(self.search_changed.emit)

        # Add clear button (X icon) inside the search input
        # Use simple text "×" character as icon (nothing fancy as requested)
        clear_action = QAction("×", self._search_input)
        clear_action.setToolTip("Clear search")
        clear_action.triggered.connect(self._clear_search)
        self._search_input.addAction(clear_action, QLineEdit.TrailingPosition)

        # Show/hide clear button based on text
        self._search_input.textChanged.connect(self._update_clear_button_visibility)
        self._update_clear_button_visibility()  # Initial state

        row3.addWidget(self._search_input)

        main_layout.addLayout(row3)

        self.setLayout(main_layout)

    def get_search_text(self) -> str:
        """Get current search text."""
        return self._search_input.text().strip()

    def _clear_search(self) -> None:
        """Clear the search input."""
        self._search_input.clear()

    def _update_clear_button_visibility(self) -> None:
        """Show or hide the clear button based on whether there's text."""
        # Get the clear action (last action added)
        actions = self._search_input.actions()
        if actions:
            clear_action = actions[-1]  # Last action is the clear button
            # Enable/disable based on whether there's text
            clear_action.setEnabled(bool(self._search_input.text()))

    def is_minify_enabled(self) -> bool:
        """Get whether minify is enabled."""
        return self._minify_checkbox.isChecked()

    def get_ignore_pattern(self) -> tuple[str, bool]:
        """Get ignore pattern and standard filters state.

        Returns:
            Tuple of (pattern: str, use_standard_filters: bool)
            use_standard_filters=True means use standard filters (ignore custom pattern)
            use_standard_filters=False means apply custom pattern
        """
        pattern = self._ignore_pattern_input.text().strip()
        use_standard_filters = self._standard_filters_checkbox.isChecked()
        return pattern, use_standard_filters

    def _on_ignore_pattern_changed(self) -> None:
        """Handle ignore pattern input or checkbox change."""
        pattern, use_standard_filters = self.get_ignore_pattern()
        self.ignore_pattern_changed.emit(pattern, use_standard_filters)

    def _on_path_entered(self) -> None:
        """Handle Enter key press in path input."""
        path = self._path_input.currentText().strip()
        if path:
            # Expand ~ if present (Path.expanduser handles this)
            from pathlib import Path

            expanded_path = str(Path(path).expanduser())
            self.path_changed.emit(expanded_path)

    def _on_path_selected(self, index: int) -> None:
        """Handle path selection from dropdown."""
        # Only emit if it's a dropdown selection (index >= 0 means item selected, not typed)
        if index >= 0:
            # Try to get full path from item data first, fallback to displayed text
            full_path = self._path_input.itemData(index)
            if full_path and isinstance(full_path, str):
                path = full_path
            else:
                # Fallback: get the text from the selected item
                path = self._path_input.itemText(index).strip()
            if path:
                # Update the edit text to show the shortened path
                display_path = shorten_home_path(path)
                self._path_input.setEditText(display_path)
                # Clear focus from the input to move focus elsewhere
                self._path_input.clearFocus()
                # Emit path change signal with full path to trigger directory change
                self.path_changed.emit(path)

    def _on_browse_clicked(self) -> None:
        """Handle browse button click - open directory dialog."""
        current_path = self._path_input.currentText().strip()
        initial_dir = current_path if current_path else str(Path.home())

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            initial_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if directory:
            self.set_path(directory)
            self.path_changed.emit(directory)

    def set_path(self, path: str) -> None:
        """Set the current path in the input field."""
        # #region agent log
        import json

        log_path = r"c:\Users\jiuvi\Documents\GitHub\ChatGPT-Feeder\.cursor\debug.log"
        current_text = self._path_input.currentText()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "E",
                        "location": "toolbar.py:741",
                        "message": "set_path called",
                        "data": {"new_path": path, "current_text_before": current_text},
                        "timestamp": int(__import__("time").time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion
        # Block signals to avoid triggering path_changed
        self._path_input.blockSignals(True)
        # Shorten home directory to ~ for display
        display_path = shorten_home_path(path)
        self._path_input.setEditText(display_path)
        self._path_input.blockSignals(False)

    def set_recent_directories(
        self, directories: list[str], current_path: str | None = None
    ) -> None:
        """Update the recent directories dropdown.

        Args:
            directories: List of recent directory paths
            current_path: Current directory path to exclude from dropdown (optional)
        """
        # Get current path from input if not provided
        if current_path is None:
            current_path = self._path_input.currentText().strip()

        self._path_input.blockSignals(True)
        self._path_input.clear()

        # Filter out current directory from dropdown to avoid duplicates
        filtered_dirs = [d for d in directories if d != current_path]
        # Store full paths as item data, but display shortened paths
        for full_path in filtered_dirs:
            display_path = shorten_home_path(full_path)
            index = self._path_input.count()
            self._path_input.addItem(display_path)
            # Store full path as item data for retrieval
            self._path_input.setItemData(index, full_path)

        # Restore current path if it exists (shortened for display)
        if current_path:
            display_path = shorten_home_path(current_path)
            self._path_input.setEditText(display_path)
        self._path_input.blockSignals(False)
        # Hide dropdown arrow when there are no recent directories
        self._update_dropdown_arrow_visibility()

    def _update_dropdown_arrow_visibility(self) -> None:
        """Show or hide the dropdown arrow based on whether there are items."""
        update_dropdown_arrow_visibility(self._path_input)
