"""Main application window."""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.components.file_tree import FileTreeWidget
from src.components.toolbar import Toolbar
from src.components.tree_status import TreeStatusWidget
from src.config import APP_NAME, ICON_PATH, MAX_FILES_HARD_LIMIT
from src.services.file_service import FileService
from src.services.scan_coordinator import ScanCoordinator
from src.services.state_service import StateService
from src.utils.clipboard import copy_to_clipboard
from src.utils.content_formatter import format_files_for_llm
from src.utils.paths import validate_directory_path
from src.utils.tokens import (
    CURSOR_CONTEXT,
    GEMINI_3_PRO_CONTEXT,
    GPT_4_1_CONTEXT,
    GPT_5_CONTEXT,
    estimate_tokens,
)
from src.workers import FileReaderWorker, FileScannerWorker


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_directory = Path.cwd()
        self._files: list[Path] = []
        self._pending_directory_scan = False
        self._last_directory_counts: dict[Path, int] | None = None
        self._scanner_worker: FileScannerWorker | None = None
        self._selection_debounce_timer: QTimer | None = (
            None  # Debounce selection changes
        )
        self._file_reader_worker: FileReaderWorker | None = (
            None  # Worker for async file reading
        )

        # Services
        self._state_service = StateService()
        self._state_service.set_current_directory(self._current_directory)
        self._file_service = FileService()
        self._scan_coordinator = ScanCoordinator()

        self._setup_ui()
        self._load_state()
        self._setup_shortcuts()
        # Set initial idle status, then scan
        self._tree_status.set_idle()
        # On startup, scan for extensions first, then files
        self._pending_directory_scan = True
        self._scan_current_directory_for_extensions()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle(APP_NAME)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH.absolute())))

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Toolbar
        self._toolbar = Toolbar()
        self._toolbar.setObjectName("toolbar")
        self._toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._toolbar.expand_all_clicked.connect(self._on_expand_all)
        self._toolbar.collapse_all_clicked.connect(self._on_collapse_all)
        self._toolbar.extension_filter.extension_changed.connect(
            self._on_extension_changed
        )
        self._toolbar.extension_filter.extensions_updated.connect(
            self._on_extensions_updated
        )
        # Track if we need to restore "any" after extensions are loaded
        self._pending_restore_any = False
        self._toolbar.search_changed.connect(self._on_search_changed)
        self._toolbar.path_changed.connect(self._on_path_changed)
        self._toolbar.ignore_pattern_changed.connect(self._on_ignore_pattern_changed)
        layout.addWidget(self._toolbar)

        # File tree
        self._tree = FileTreeWidget()
        self._tree.selection_changed.connect(self._on_selection_changed)
        self._tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._tree)

        # Tree status indicator
        self._tree_status = TreeStatusWidget()
        self._tree_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._tree_status)

        # Submit button
        from src.utils.icons import get_ui_icon

        copy_icon = get_ui_icon("copy")
        self._submit_btn = QPushButton("Copy to Clipboard")
        if not copy_icon.isNull():
            self._submit_btn.setIcon(copy_icon)
        self._submit_btn.setObjectName("submitButton")
        self._submit_btn.clicked.connect(self._on_submit)
        self._submit_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Improve button text styling
        self._submit_btn.setStyleSheet(
            """
            QPushButton#submitButton {
                font-size: 10pt;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
        """
        )
        layout.addWidget(self._submit_btn)

        central.setLayout(layout)

        # Let Qt calculate minimum width from child widgets, then set reasonable initial size
        # Qt will automatically enforce minimum width based on child widget constraints
        self.resize(450, 700)

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Ctrl+A: Select all
        QShortcut(QKeySequence("Ctrl+A"), self, self._on_select_all)

        # Ctrl+D: Deselect all
        QShortcut(QKeySequence("Ctrl+D"), self, self._on_deselect_all)

        # Ctrl+Enter: Submit (Copy)
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_submit)

        # Ctrl+Shift+C: Alternative Copy Shortcut
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, self._on_submit)

    def _load_state(self) -> None:
        """Load application state."""
        state = self._state_service.load_state()

        # Load recent directories and update toolbar
        recent_dirs = state.get("recent_directories", [])
        # Add current directory to recent directories if not already present
        current_dir_str = str(self._current_directory)
        if current_dir_str not in recent_dirs:
            recent_dirs = self._state_service.add_recent_directory(
                recent_dirs, current_dir_str
            )
            # Save updated recent directories to state
            selected_tuples = state.get("selected_files", set())
            if isinstance(selected_tuples, list):
                selected_tuples = set(tuple(f) for f in selected_tuples)
            self._state_service.save_state(
                selected_tuples,
                state.get("select_all_state", False),
                recent_dirs,
            )
        self._toolbar.set_recent_directories(recent_dirs, current_dir_str)

        # Set current path in toolbar
        self._toolbar.set_path(current_dir_str)

        # Update available extensions for initial directory - always use most common
        # Extension is no longer saved/restored from state
        self._pending_restore_any = False
        _, use_standard_filters = self._toolbar.get_ignore_pattern()
        self._toolbar.extension_filter.update_available_extensions(
            self._current_directory,
            set_to_most_common=True,
            use_standard_filters=use_standard_filters,
        )

    def _scan_current_directory_for_extensions(self) -> None:
        """Scan directory to collect extensions (used when directory changes, non-blocking).

        Optimized: Reuses extension counts from file scan if available, avoiding redundant scan.
        """
        # Check if we have cached extension counts for this directory
        extension_counts = self._scan_coordinator.get_cached_extension_counts(
            self._current_directory
        )
        if extension_counts:
            # Reuse cached extension counts - no need for separate scan
            self._toolbar.extension_filter._update_extensions_from_list(
                extension_counts
            )
            # Trigger file scan if pending
            if self._pending_directory_scan:
                self._pending_directory_scan = False
                self._scan_current_directory()
            return

        # No cache available - need to scan, but we'll get extensions from the file scan
        # Just trigger the file scan directly with a dummy extension to collect all extensions
        # Cancel any existing scan
        self._cleanup_scanner_worker()

        # Show loading status
        self._tree_status.set_loading()
        self._tree.show_loading()

        # Create worker to scan for extensions (use empty extension to get all files)
        # Always collect extensions for this scan since we need them
        _, use_standard_filters = self._toolbar.get_ignore_pattern()
        self._scanner_worker = FileScannerWorker(
            self._current_directory,
            "",  # Empty extension to collect all files and their extensions
            check_limit=None,
            collect_extensions=True,
            use_standard_filters=use_standard_filters,
        )
        self._scanner_worker.finished.connect(
            self._on_extension_scan_finished, Qt.QueuedConnection
        )
        self._scanner_worker.start()

    def _on_extension_scan_finished(self, result: tuple) -> None:
        """Handle completion of async extension scan."""
        try:
            _, _, _, extension_counts, error = result

            if error:
                self._tree_status.set_error(error)
                # Fallback to old method on error
                _, use_standard_filters = self._toolbar.get_ignore_pattern()
                self._toolbar.extension_filter.update_available_extensions(
                    self._current_directory,
                    set_to_most_common=True,
                    use_standard_filters=use_standard_filters,
                )
                return

            # Cache extension counts for this directory
            if extension_counts:
                self._scan_coordinator.cache_extension_counts(
                    self._current_directory, extension_counts
                )

            # Update extension dropdown
            if extension_counts:
                self._toolbar.extension_filter._update_extensions_from_list(
                    extension_counts
                )
            else:
                # Fallback to old method if no extensions found
                _, use_standard_filters = self._toolbar.get_ignore_pattern()
                self._toolbar.extension_filter.update_available_extensions(
                    self._current_directory,
                    set_to_most_common=True,
                    use_standard_filters=use_standard_filters,
                )

            # Note: The extensions_updated signal will trigger _on_extensions_updated,
            # which will handle triggering the file scan if _pending_directory_scan is True
        except Exception as e:
            self._handle_error("Error processing extension scan", e)

    def _scan_current_directory(self) -> None:
        """Scan current directory for files (non-blocking)."""
        # Cancel any existing scan
        self._cleanup_scanner_worker()

        # Show loading status
        self._tree_status.set_loading()
        self._tree.show_loading()  # Show loading indicator in tree

        extension = self._toolbar.extension_filter.get_extension()

        # Check if we already have extension counts cached - if so, skip collection
        should_collect = self._scan_coordinator.should_collect_extensions(
            self._current_directory
        )

        # Get filter settings
        _, use_standard_filters = self._toolbar.get_ignore_pattern()

        # Create and start worker thread
        self._scanner_worker = FileScannerWorker(
            self._current_directory,
            extension,
            check_limit=MAX_FILES_HARD_LIMIT + 1,
            collect_extensions=should_collect,
            use_standard_filters=use_standard_filters,
        )
        # Use Qt.QueuedConnection to ensure signal is processed in main thread
        self._scanner_worker.finished.connect(
            self._on_scan_finished, Qt.QueuedConnection
        )
        self._scanner_worker.start()

    def _on_scan_finished(self, result: tuple) -> None:
        """Handle completion of async file scan."""
        try:
            files, file_count, directory_counts, extension_counts, error = result
        except (ValueError, TypeError) as e:
            import traceback

            traceback.print_exc()
            self._tree_status.set_error(f"Error processing scan results: {e}")
            return

        try:
            if error:
                self._tree_status.set_error(error)
                return

            extension = self._toolbar.extension_filter.get_extension()
            # #region agent log
            with open(
                r"c:\Users\jiuvi\Documents\GitHub\ChatGPT-Feeder\.cursor\debug.log",
                "a",
                encoding="utf-8",
            ) as f:
                import json

                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "D",
                            "location": "main_window.py:303",
                            "message": "scan finished, processing results",
                            "data": {
                                "extension": extension,
                                "files_count": len(files),
                                "file_count": file_count,
                                "extension_counts": extension_counts,
                                "sample_files": [str(f) for f in files[:5]],
                            },
                            "timestamp": int(__import__("time").time() * 1000),
                        }
                    )
                    + "\n"
                )
            # #endregion

            # Validate and handle file count warnings
            if not self._validate_and_handle_file_count(
                file_count, extension, len(files)
            ):
                return

            # Process scan results
            self._process_scan_results(
                files, file_count, directory_counts, extension_counts, extension
            )

        except Exception as e:
            self._handle_error("Error processing file scan", e)

    def _validate_and_handle_file_count(
        self, file_count: int, extension: str, files_found: int
    ) -> bool:
        """Validate file count and show warnings if needed.

        Args:
            file_count: Total file count
            extension: File extension being scanned
            files_found: Number of files in the result list

        Returns:
            True if scan should proceed, False if should stop
        """
        should_proceed, warning_msg = self._scan_coordinator.validate_file_count(
            file_count, extension
        )

        if not should_proceed:
            self._tree_status.set_idle()
            QMessageBox.warning(
                self,
                "Too Many Files",
                warning_msg or "Too many files to scan.",
                QMessageBox.Ok,
            )
            return False

        # If we hit the check limit, we need to do a full scan
        if files_found == MAX_FILES_HARD_LIMIT + 1:
            # We stopped early, need to check if user wants to proceed
            if self._scan_coordinator.should_show_warning(file_count):
                reply = QMessageBox.warning(
                    self,
                    "Large Directory Warning",
                    warning_msg
                    or f"This directory contains at least {file_count:,} {extension} files.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    self._tree_status.set_idle()
                    return False

                # User wants to continue, do full scan in background
                should_collect = self._scan_coordinator.should_collect_extensions(
                    self._current_directory
                )
                _, use_standard_filters = self._toolbar.get_ignore_pattern()
                self._scanner_worker = FileScannerWorker(
                    self._current_directory,
                    extension,
                    check_limit=None,
                    collect_extensions=should_collect,
                    use_standard_filters=use_standard_filters,
                )
                self._scanner_worker.finished.connect(
                    self._on_scan_finished, Qt.QueuedConnection
                )
                self._scanner_worker.start()
                return False  # Don't process current results, waiting for full scan
        elif self._scan_coordinator.should_show_warning(file_count):
            # We have the full list, but it's large - warn user
            reply = QMessageBox.warning(
                self,
                "Large Directory Warning",
                warning_msg
                or f"This directory contains {file_count:,} {extension} files.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                self._tree_status.set_idle()
                return False

        return True

    def _process_scan_results(
        self,
        files: list[Path],
        _file_count: int,
        directory_counts: dict[Path, int],
        extension_counts: dict[str, int],
        extension: str,
    ) -> None:
        """Process and display scan results.

        Args:
            files: List of file paths found
            file_count: Total file count
            directory_counts: Dictionary of directory file counts
            extension_counts: Dictionary of extension counts
            extension: File extension being scanned
        """
        # Update with results
        self._files = files

        # Store directory counts for use in re-population
        self._last_directory_counts = directory_counts

        # Cache extension counts for this directory to avoid redundant scans
        if extension_counts:
            self._scan_coordinator.cache_extension_counts(
                self._current_directory, extension_counts
            )

        # Update toolbar path display
        # #region agent log
        import json

        log_path = r"c:\Users\jiuvi\Documents\GitHub\ChatGPT-Feeder\.cursor\debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "main_window.py:459",
                        "message": "_process_scan_results updating path",
                        "data": {
                            "current_directory": str(self._current_directory),
                            "files_count": len(files),
                            "first_file_parent": (
                                str(files[0].parent) if files else None
                            ),
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion
        self._toolbar.set_path(str(self._current_directory))

        # Preserve current selection from tree before repopulating
        current_selection = set(self._tree.get_selected_files())
        # Merge with saved state (current selection takes precedence)
        saved_selection = self._state_service.get_selected_paths_from_state()
        selected_paths = current_selection | saved_selection

        search_text = self._toolbar.get_search_text()
        # #region agent log
        with open(
            r"c:\Users\jiuvi\Documents\GitHub\ChatGPT-Feeder\.cursor\debug.log",
            "a",
            encoding="utf-8",
        ) as f:
            import json

            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "B",
                        "location": "main_window.py:426",
                        "message": "calling populate",
                        "data": {
                            "extension": extension,
                            "extension_type": type(extension).__name__,
                            "files_count": len(self._files),
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion
        # Get ignore pattern settings
        ignore_pattern, use_standard_filters = self._toolbar.get_ignore_pattern()

        self._tree.populate(
            self._files,
            extension,
            selected_paths,
            search_text,
            self._current_directory,
            directory_counts,
            ignore_prefix=ignore_pattern if ignore_pattern else None,
            use_standard_filters=use_standard_filters,
        )

        # Update status indicator
        if len(self._files) > 0:
            # Initially show file count only, tokens and lines will be calculated asynchronously
            self._tree_status.set_loaded(len(self._files), extension, 0, 0)
            # Read all files asynchronously to calculate tokens and line count
            self._calculate_all_files_stats()
        else:
            self._tree_status.set_empty(extension)

    def _cleanup_scanner_worker(self) -> None:
        """Clean up scanner worker thread if it's running."""
        if self._scanner_worker and self._scanner_worker.isRunning():
            self._scanner_worker.terminate()
            self._scanner_worker.wait()
            self._scanner_worker = None

    def _on_search_changed(self, text: str) -> None:
        """Handle search filter change."""
        extension = self._toolbar.extension_filter.get_extension()

        # Preserve current selection from tree before repopulating
        current_selection = set(self._tree.get_selected_files())
        # Merge with saved state (current selection takes precedence)
        saved_selection = self._state_service.get_selected_paths_from_state()
        selected_paths = current_selection | saved_selection

        # Get ignore pattern settings
        ignore_pattern, use_standard_filters = self._toolbar.get_ignore_pattern()

        self._tree.populate(
            self._files,
            extension,
            selected_paths,
            text,
            self._current_directory,
            ignore_prefix=ignore_pattern if ignore_pattern else None,
            use_standard_filters=use_standard_filters,
        )

    def _on_ignore_pattern_changed(
        self, pattern: str, use_standard_filters: bool
    ) -> None:
        """Handle ignore pattern change - re-populate tree with new filter."""
        extension = self._toolbar.extension_filter.get_extension()

        # Re-scan extensions with new filter state to ensure extension list is accurate
        # Clear cached extension counts since filters have changed
        self._scan_coordinator.clear_extension_cache(self._current_directory)
        # Re-scan extensions with current filter settings
        self._toolbar.extension_filter.update_available_extensions(
            self._current_directory,
            set_to_most_common=False,  # Preserve current extension selection
            use_standard_filters=use_standard_filters,
        )

        # Preserve current selection from tree before repopulating
        current_selection = set(self._tree.get_selected_files())
        # Merge with saved state (current selection takes precedence)
        saved_selection = self._state_service.get_selected_paths_from_state()
        selected_paths = current_selection | saved_selection

        search_text = self._toolbar.get_search_text()

        # Get directory counts if available (from last scan)
        directory_counts = None
        if hasattr(self, "_last_directory_counts"):
            directory_counts = self._last_directory_counts

        self._tree.populate(
            self._files,
            extension,
            selected_paths,
            search_text,
            self._current_directory,
            directory_counts,
            ignore_prefix=pattern if pattern else None,
            use_standard_filters=use_standard_filters,
        )

    def _on_path_changed(self, path_str: str) -> None:
        """Handle path change from toolbar."""
        # #region agent log
        import json

        log_path = r"c:\Users\jiuvi\Documents\GitHub\ChatGPT-Feeder\.cursor\debug.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A",
                        "location": "main_window.py:564",
                        "message": "_on_path_changed entry",
                        "data": {
                            "path_str": path_str,
                            "current_directory_before": str(self._current_directory),
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion

        if not path_str:
            self._tree_status.set_idle()
            return

        try:
            is_valid, new_path, error_msg = validate_directory_path(path_str)

            # #region agent log
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "B",
                            "location": "main_window.py:571",
                            "message": "path validation result",
                            "data": {
                                "is_valid": is_valid,
                                "new_path": str(new_path) if new_path else None,
                                "error_msg": error_msg,
                                "path_str": path_str,
                            },
                            "timestamp": int(__import__("time").time() * 1000),
                        }
                    )
                    + "\n"
                )
            # #endregion

            if not is_valid:
                self._tree_status.set_error(error_msg or "Invalid path")
                QMessageBox.warning(
                    self,
                    "Invalid Path",
                    error_msg or f"The path is invalid:\n{path_str}",
                )
                # Reset to current directory
                self._toolbar.set_path(str(self._current_directory))
                return

            # Update current directory
            self._current_directory = new_path
            self._state_service.set_current_directory(new_path)

            # #region agent log
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "C",
                            "location": "main_window.py:585",
                            "message": "current_directory updated",
                            "data": {
                                "current_directory_after": str(self._current_directory),
                                "new_path": str(new_path),
                            },
                            "timestamp": int(__import__("time").time() * 1000),
                        }
                    )
                    + "\n"
                )
            # #endregion

            # Update recent directories
            state = self._state_service.load_state()
            recent_dirs = state.get("recent_directories", [])
            recent_dirs = self._state_service.add_recent_directory(
                recent_dirs, str(self._current_directory)
            )
            self._toolbar.set_recent_directories(
                recent_dirs, str(self._current_directory)
            )
            self._toolbar.set_path(str(self._current_directory))

            # Move focus to tree after directory change
            # Use QTimer.singleShot to defer focus change until after event loop processes current events
            QTimer.singleShot(0, lambda: self._tree.setFocus())

            # When directory changes, check if we have cached extension counts
            # If not, scan to collect extensions first, then trigger file scan
            self._pending_directory_scan = True
            self._scan_current_directory_for_extensions()

            # Save state with updated recent directories
            selected_tuples = state.get("selected_files", set())
            if isinstance(selected_tuples, list):
                selected_tuples = set(tuple(f) for f in selected_tuples)
            self._state_service.save_state(
                selected_tuples,
                state.get("select_all_state", False),
                recent_dirs,
            )

        except Exception as e:
            self._handle_error("Failed to open directory", e, show_message=True)
            # Reset to current directory
            self._toolbar.set_path(str(self._current_directory))

    def _on_extension_changed(self, _extension: str) -> None:
        """Handle extension filter change."""
        # Only scan if not waiting for directory change scan
        if not self._pending_directory_scan:
            self._scan_current_directory()

    def _on_extensions_updated(self) -> None:
        """Handle extension list update completion."""
        # If we need to restore "any" selection (from state load), do it now
        if getattr(self, "_pending_restore_any", False):
            self._pending_restore_any = False
            self._toolbar.extension_filter.set_extension("")

        # If we're waiting for a directory change scan, trigger it now
        if self._pending_directory_scan:
            self._pending_directory_scan = False
            self._scan_current_directory()

    def _on_expand_all(self) -> None:
        """Expand all tree items."""
        self._tree.expandAll()

    def _on_collapse_all(self) -> None:
        """Collapse all tree items."""
        self._tree.collapseAll()

    def closeEvent(self, event) -> None:
        """Handle window close event - cleanup worker threads."""
        self._cleanup_scanner_worker()
        if self._file_reader_worker and self._file_reader_worker.isRunning():
            self._file_reader_worker.terminate()
            self._file_reader_worker.wait()
        super().closeEvent(event)

    def _on_select_all(self) -> None:
        """Select all files."""
        self._tree.select_all(True)

    def _on_deselect_all(self) -> None:
        """Deselect all files."""
        self._tree.select_all(False)

    def _on_selection_changed(self) -> None:
        """Handle selection change with debouncing to avoid reading files on every checkbox change."""
        # Cancel any pending debounce timer
        if self._selection_debounce_timer:
            self._selection_debounce_timer.stop()

        # Update count immediately (fast operation)
        count = self._tree.get_selected_count()
        total = len(self._files)

        if count == 0:
            # No selection
            return

        # Debounce the expensive file reading operation
        # Wait 300ms after last selection change before reading files
        self._selection_debounce_timer = QTimer()
        self._selection_debounce_timer.setSingleShot(True)
        self._selection_debounce_timer.timeout.connect(self._process_selection_change)
        self._selection_debounce_timer.start(300)  # 300ms debounce delay

    def _process_selection_change(self) -> None:
        """Process selection change after debounce delay - reads files asynchronously."""
        count = self._tree.get_selected_count()
        total = len(self._files)

        if count > 0:
            # Get selected files
            selected = self._tree.get_selected_files()

            # Cancel any existing file reader worker
            if self._file_reader_worker and self._file_reader_worker.isRunning():
                self._file_reader_worker.terminate()
                self._file_reader_worker.wait()

            # Read files asynchronously with caching
            self._file_reader_worker = FileReaderWorker(
                selected, self._file_service.get_cache()
            )
            self._file_reader_worker.finished.connect(
                self._on_files_read, Qt.QueuedConnection
            )
            self._file_reader_worker.start()

    def _on_files_read(self, content_map: dict[str, str]) -> None:
        """Handle completion of async file reading."""
        count = self._tree.get_selected_count()
        total = len(self._files)

        if count > 0 and content_map:
            # Process file contents
            minify_enabled = self._toolbar.is_minify_enabled()
            text = format_files_for_llm(content_map, minify=minify_enabled)
            tokens = estimate_tokens(text)

            # Calculate context percentages
            cursor_pct = (tokens / CURSOR_CONTEXT) * 100
            gpt5_pct = (tokens / GPT_5_CONTEXT) * 100
            gpt41_pct = (tokens / GPT_4_1_CONTEXT) * 100
            gemini_pct = (tokens / GEMINI_3_PRO_CONTEXT) * 100

    def _calculate_all_files_stats(self) -> None:
        """Calculate tokens and line count for all files in the tree."""
        if not self._files:
            return

        # Cancel any existing file reader worker
        if self._file_reader_worker and self._file_reader_worker.isRunning():
            self._file_reader_worker.terminate()
            self._file_reader_worker.wait()

        # Read all files asynchronously
        self._file_reader_worker = FileReaderWorker(
            self._files, self._file_service.get_cache()
        )
        self._file_reader_worker.finished.connect(
            self._on_all_files_read, Qt.QueuedConnection
        )
        self._file_reader_worker.start()

    def _on_all_files_read(self, content_map: dict[str, str]) -> None:
        """Handle completion of reading all files for stats calculation."""
        if not content_map or not self._files:
            return

        # Process all file contents
        minify_enabled = self._toolbar.is_minify_enabled()
        text = format_files_for_llm(content_map, minify=minify_enabled)
        tokens = estimate_tokens(text)
        line_count = text.count("\n") + 1 if text else 0

        # Calculate context percentages
        percentages = {
            "Cursor": (tokens / CURSOR_CONTEXT) * 100,
            "GPT-5": (tokens / GPT_5_CONTEXT) * 100,
            "Gemini 3 Pro": (tokens / GEMINI_3_PRO_CONTEXT) * 100,
            "GPT-4.1": (tokens / GPT_4_1_CONTEXT) * 100,
        }

        # Update tree status with calculated values
        extension = self._toolbar.extension_filter.get_extension()
        self._tree_status.set_loaded(
            len(self._files), extension, tokens, line_count, percentages
        )

    def _on_submit(self) -> None:
        """Handle submit button click."""
        selected = self._tree.get_selected_files()

        if not selected:
            QMessageBox.information(
                self, "No Selection", "Please select at least one file."
            )
            return

        # Collect and format file contents using service
        minify_enabled = self._toolbar.is_minify_enabled()
        text = self._file_service.format_files_for_llm(selected, minify=minify_enabled)

        # Copy to clipboard
        copy_to_clipboard(text, lambda msg: None)

        # Save state
        selected_tuples = self._state_service.paths_to_state_tuples(selected)

        # Get current recent directories from state
        state = self._state_service.load_state()
        recent_dirs = state.get("recent_directories", [])

        self._state_service.save_state(
            selected_tuples,
            False,  # select_all_state
            recent_dirs,
        )

    def _handle_error(
        self, context: str, error: Exception, show_message: bool = False
    ) -> None:
        """Handle errors consistently.

        Args:
            context: Context description of the error
            error: Exception that occurred
            show_message: Whether to show a message box
        """
        import traceback

        error_msg = f"{context}: {str(error)}"
        print(f"ERROR in {context}: {error}")
        traceback.print_exc()
        self._tree_status.set_error(error_msg)

        if show_message:
            QMessageBox.warning(self, "Error", f"{context}:\n{str(error)}")
