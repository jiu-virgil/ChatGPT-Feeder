"""File tree widget component."""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from src.config import (
    MAX_FILES_PER_DIRECTORY,
    STANDARD_DIRECTORY_NAMES,
    STANDARD_FILE_NAME_PREFIXES,
    STANDARD_FILE_NAMES,
)
from src.utils.extensions import matches_extension
from src.utils.file_reader import open_file_in_editor
from src.utils.icons import get_folder_icon, get_icon_for_extension


class CheckableTreeItem(QTreeWidgetItem):
    """Tree item with checkbox support."""

    def __init__(self, text: str, parent: QTreeWidgetItem | None = None):
        super().__init__(parent)
        self.setText(0, text)
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        self.setCheckState(0, Qt.Unchecked)


class FileTreeWidget(QTreeWidget):
    """File tree widget with checkbox support and VS Code icons."""

    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(True)
        self.setAnimated(False)
        self.setIndentation(16)
        self.setIconSize(QSize(16, 16))  # Ensure standard icon size

        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)
        self.itemChanged.connect(self._on_item_changed)
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)

        self._file_path_map: dict[QTreeWidgetItem, Path] = {}
        self._locked_directories: set[Path] = set()  # Track locked directory paths
        self._directory_item_map: dict[Path, QTreeWidgetItem] = (
            {}
        )  # Map directory paths to tree items

        # Async population state
        self._pending_files: list[Path] = []
        self._pending_populate_state: dict = {}
        self._is_populating: bool = False
        self._populate_timer: QTimer | None = None

        # Deferred icon loading
        self._pending_icon_updates: list[tuple[QTreeWidgetItem, str, str]] = (
            []
        )  # (item, icon_type, identifier)
        self._icon_update_timer: QTimer | None = None
        self._placeholder_icon = QIcon()  # Empty placeholder icon

    def show_loading(self) -> None:
        """Show loading indicator in the tree."""
        # Cancel any ongoing population
        self._cancel_population()
        self.clear()
        self._file_path_map.clear()
        self._locked_directories.clear()
        self._directory_item_map.clear()

        # Add a loading item
        loading_item = CheckableTreeItem("Loading...")
        loading_item.setFlags(Qt.NoItemFlags)  # Disable interaction
        self.addTopLevelItem(loading_item)

    def _cancel_population(self) -> None:
        """Cancel any ongoing async population."""
        if self._populate_timer:
            self._populate_timer.stop()
            self._populate_timer = None
        if self._icon_update_timer:
            self._icon_update_timer.stop()
            self._icon_update_timer = None
        self._is_populating = False
        self._pending_files = []
        self._pending_populate_state = {}
        self._pending_icon_updates = []

    def populate(
        self,
        files: list[Path],
        extension: str,
        selected_paths: set[Path],
        search_filter: str = "",
        base_directory: Path | None = None,
        directory_counts: dict[Path, int] | None = None,
        ignore_prefix: str | None = None,
        use_standard_filters: bool = True,
    ) -> None:
        """Populate tree with files asynchronously to prevent UI freezing."""
        # Cancel any ongoing population
        self._cancel_population()

        self.clear()
        self._file_path_map.clear()
        self._locked_directories.clear()
        self._directory_item_map.clear()

        # Identify locked directories based on file counts
        if directory_counts:
            for dir_path, file_count in directory_counts.items():
                if file_count > MAX_FILES_PER_DIRECTORY:
                    self._locked_directories.add(dir_path)

        # Root Item
        root_name = base_directory.name if base_directory else "Project Root"
        root_item = CheckableTreeItem(root_name)

        # Set Root Icon (Open)
        root_item.setIcon(0, get_folder_icon(root_name, is_open=True))
        root_item.setExpanded(True)
        self.addTopLevelItem(root_item)

        # Filter files by extension and search
        search_lower = search_filter.lower()
        filtered_files = []
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
                        "hypothesisId": "A",
                        "location": "file_tree.py:110",
                        "message": "populate called",
                        "data": {
                            "extension": extension,
                            "extension_type": type(extension).__name__,
                            "files_count": len(files),
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion
        for file_path in files:
            # Skip extension filter if extension is empty string (means "any")
            # Support comma-separated extensions
            # #region agent log
            should_skip = bool(
                extension and not matches_extension(file_path.suffix, extension)
            )
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
                            "hypothesisId": "A",
                            "location": "file_tree.py:181",
                            "message": "checking file extension with fix",
                            "data": {
                                "file_path": str(file_path),
                                "file_suffix": file_path.suffix,
                                "extension": extension,
                                "extension_is_empty": extension == "",
                                "should_skip": should_skip,
                                "condition_eval": f"extension={extension!r} and suffix={file_path.suffix!r} != extension",
                            },
                            "timestamp": int(__import__("time").time() * 1000),
                        }
                    )
                    + "\n"
                )
            # #endregion
            if should_skip:
                continue

            # Apply standard filters or custom ignore prefix
            should_ignore_file = False

            if use_standard_filters:
                # Apply standard filters: prefixes, file names, and directory names
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
            elif ignore_prefix:
                # Apply custom ignore prefix pattern
                if file_path.name.startswith(ignore_prefix):
                    should_ignore_file = True

            if should_ignore_file:
                continue

            try:
                rel_path = (
                    file_path.relative_to(base_directory)
                    if base_directory
                    else file_path
                )
            except ValueError:
                rel_path = file_path
            if search_lower and search_lower not in str(rel_path).lower():
                continue
            filtered_files.append(file_path)

        # Store state for async processing
        self._pending_files = filtered_files
        total_files = len(filtered_files)
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
                        "hypothesisId": "C",
                        "location": "file_tree.py:200",
                        "message": "filtered_files count",
                        "data": {
                            "total_files": total_files,
                            "filtered_files_count": len(filtered_files),
                            "original_files_count": len(files),
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion

        # Calculate adaptive batch size based on file count
        # Small projects (< 100 files): 100 items per batch
        # Medium projects (100-1000 files): 200 items per batch
        # Large projects (1000-10000 files): 300 items per batch
        # Very large projects (> 10000 files): 500 items per batch (capped)
        if total_files < 100:
            adaptive_batch_size = 100
        elif total_files < 1000:
            adaptive_batch_size = 200
        elif total_files < 10000:
            adaptive_batch_size = 300
        else:
            adaptive_batch_size = 500

        self._pending_populate_state = {
            "extension": extension,
            "selected_paths": selected_paths,
            "search_filter": search_filter,
            "base_directory": base_directory,
            "directory_counts": directory_counts,
            "root_item": root_item,
            "path_map": {},  # Will be built during processing
            "batch_size": adaptive_batch_size,
        }
        self._is_populating = True

        # Start async processing
        self._process_population_batch()

    def _process_population_batch(self) -> None:
        """Process a batch of files asynchronously."""
        if not self._is_populating or not self._pending_files:
            # Finished - finalize tree
            self._finalize_population()
            return

        state = self._pending_populate_state
        root_item = state["root_item"]
        path_map = state["path_map"]
        extension = state["extension"]
        selected_paths = state["selected_paths"]
        base_directory = state["base_directory"]
        directory_counts = state["directory_counts"]
        batch_size = state.get("batch_size", 200)  # Default to 200 if not set

        # Process batch with adaptive size
        batch = self._pending_files[:batch_size]
        self._pending_files = self._pending_files[batch_size:]
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
                        "hypothesisId": "C",
                        "location": "file_tree.py:249",
                        "message": "processing batch",
                        "data": {
                            "batch_size": len(batch),
                            "remaining_files": len(self._pending_files),
                            "extension": extension,
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion

        # Cache constants to avoid repeated Path() constructions
        root_path = Path(".")
        root_path_parent = root_path.parent

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
                        "hypothesisId": "C",
                        "location": "file_tree.py:255",
                        "message": "starting batch loop",
                        "data": {
                            "batch_size": len(batch),
                            "base_directory": (
                                str(base_directory) if base_directory else None
                            ),
                        },
                        "timestamp": int(__import__("time").time() * 1000),
                    }
                )
                + "\n"
            )
        # #endregion
        for file_path in batch:
            # Handle relativity - cache relative path
            try:
                rel_path = (
                    file_path.relative_to(base_directory)
                    if base_directory
                    else file_path
                )
            except ValueError:
                rel_path = file_path

            # Ensure parent folders exist
            parent_item = root_item
            if len(rel_path.parts) > 1:
                parent_item = self._ensure_directory_path(
                    rel_path.parts[:-1],
                    root_item,
                    root_path,
                    path_map,
                    base_directory,
                    directory_counts,
                )

            # Add File
            file_item = CheckableTreeItem(rel_path.name, parent_item)
            # Use placeholder icon initially, load real icon asynchronously
            file_item.setIcon(0, self._placeholder_icon)
            # Queue icon update for later
            self._pending_icon_updates.append((file_item, "file", file_path.suffix))
            self._file_path_map[file_item] = file_path
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
                            "hypothesisId": "C",
                            "location": "file_tree.py:300",
                            "message": "adding file to tree",
                            "data": {
                                "file_name": rel_path.name,
                                "file_path": str(file_path),
                                "parent_item": (
                                    str(parent_item.text(0)) if parent_item else None
                                ),
                                "rel_path_parts": len(rel_path.parts),
                            },
                            "timestamp": int(__import__("time").time() * 1000),
                        }
                    )
                    + "\n"
                )
            # #endregion

            if file_path in selected_paths:
                file_item.setCheckState(0, Qt.Checked)

        # Schedule next batch
        if self._pending_files:
            # Use QTimer to allow UI to process events
            self._populate_timer = QTimer()
            self._populate_timer.setSingleShot(True)
            self._populate_timer.timeout.connect(self._process_population_batch)
            self._populate_timer.start(
                0
            )  # Process next batch immediately but allow events
        else:
            # All files processed, finalize
            self._finalize_population()

    def _finalize_population(self) -> None:
        """Finalize tree population after all files are processed."""
        if not self._is_populating:
            return

        state = self._pending_populate_state
        root_item = state.get("root_item")

        if root_item:
            # Only expand all if tree is reasonably sized (< 1000 items)
            # For larger trees, only expand root to avoid UI freeze
            total_items = self._count_tree_items(root_item)
            if total_items < 1000:
                self.expandAll()
            else:
                # For large trees, only expand root level
                root_item.setExpanded(True)
                # Expand first few top-level items for better UX
                for i in range(min(5, root_item.childCount())):
                    child = root_item.child(i)
                    if child:
                        child.setExpanded(True)

            self._update_all_parent_states()
            self._update_root_item_state(root_item)

        # Clean up and start icon loading
        self._finalize_population_cleanup()

    def _count_tree_items(self, item: QTreeWidgetItem) -> int:
        """Count total items in tree starting from given item."""
        count = 1  # Count the item itself
        for i in range(item.childCount()):
            count += self._count_tree_items(item.child(i))
        return count

    def _finalize_population_cleanup(self) -> None:
        """Clean up population state after finalization."""
        # Clean up population state
        self._is_populating = False
        self._pending_files = []
        self._pending_populate_state = {}
        if self._populate_timer:
            self._populate_timer = None

        # Start deferred icon loading after tree is built
        self._start_icon_loading()

    def _build_full_directory_path(
        self, current_map_path: Path, base_directory: Path
    ) -> Path:
        """Build full directory path from relative map path.

        Args:
            current_map_path: Relative path in the map (e.g., Path("src/components"))
            base_directory: Base directory for the scan

        Returns:
            Full Path object
        """
        if current_map_path == Path("."):
            return base_directory

        # Build path incrementally from base
        full_dir_path = base_directory
        for path_part in current_map_path.parts:
            if path_part != ".":
                full_dir_path = full_dir_path / path_part
        return full_dir_path

    def _ensure_directory_path(
        self,
        path_parts: tuple,
        root_item: QTreeWidgetItem,
        root_path: Path,
        path_map: dict,
        base_directory: Path | None,
        directory_counts: dict[Path, int] | None,
    ) -> QTreeWidgetItem:
        """Ensure directory path exists in tree, creating items as needed.

        Args:
            path_parts: Tuple of path parts (excluding filename)
            root_item: Root tree item
            root_path: Path(".") constant
            path_map: Dictionary mapping relative paths to tree items
            base_directory: Base directory for building full paths
            directory_counts: Dictionary of directory file counts

        Returns:
            Parent item for the file
        """
        current_map_path = root_path
        parent_item = root_item

        for part in path_parts:
            current_map_path = current_map_path / part
            if current_map_path not in path_map:
                # Find parent item - cache parent path lookup
                current_parent = current_map_path.parent
                if current_parent == root_path:
                    p_item = root_item
                else:
                    p_item = path_map.get(current_parent, root_item)

                folder_item = CheckableTreeItem(part, p_item)
                # Use placeholder icon initially, load real icon asynchronously
                folder_item.setIcon(0, self._placeholder_icon)
                # Queue icon update for later
                self._pending_icon_updates.append((folder_item, "folder", part))
                path_map[current_map_path] = folder_item

                # Check if this directory should be locked
                if base_directory:
                    full_dir_path = self._build_full_directory_path(
                        current_map_path, base_directory
                    )

                    if full_dir_path in self._locked_directories:
                        folder_item.setChildIndicatorPolicy(
                            QTreeWidgetItem.DontShowIndicator
                        )
                        file_count = (
                            directory_counts.get(full_dir_path, 0)
                            if directory_counts
                            else 0
                        )
                        folder_item.setToolTip(
                            0,
                            f"Directory locked: contains {file_count:,} files (limit: {MAX_FILES_PER_DIRECTORY:,})",
                        )
                        # Try to set lock icon, fallback to text if icon not available
                        from src.utils.icons import get_ui_icon

                        lock_icon = get_ui_icon("lock")
                        if not lock_icon.isNull():
                            folder_item.setIcon(0, lock_icon)
                        folder_item.setText(0, f"{part} ({file_count:,} files)")
                        self._directory_item_map[full_dir_path] = folder_item

            parent_item = path_map[current_map_path]

        return parent_item

    def _start_icon_loading(self) -> None:
        """Start loading icons asynchronously for items that need them."""
        if not self._pending_icon_updates:
            return

        # Process icons in batches to avoid blocking UI
        self._process_icon_batch()

    def _process_icon_batch(self) -> None:
        """Process a batch of icon updates."""
        if not self._pending_icon_updates:
            self._icon_update_timer = None
            return

        # Process 50 icons at a time
        batch_size = 50
        batch = self._pending_icon_updates[:batch_size]
        self._pending_icon_updates = self._pending_icon_updates[batch_size:]

        for item, icon_type, identifier in batch:
            try:
                if icon_type == "file":
                    icon = get_icon_for_extension(identifier)
                else:  # folder
                    icon = get_folder_icon(identifier, is_open=False)

                if not icon.isNull():
                    item.setIcon(0, icon)
            except Exception:
                # Silently fail - icon loading is not critical
                pass

        # Schedule next batch
        if self._pending_icon_updates:
            self._icon_update_timer = QTimer()
            self._icon_update_timer.setSingleShot(True)
            self._icon_update_timer.timeout.connect(self._process_icon_batch)
            self._icon_update_timer.start(
                0
            )  # Process next batch immediately but allow events
        else:
            self._icon_update_timer = None

    def get_selected_files(self) -> list[Path]:
        selected: list[Path] = []
        for item, file_path in self._file_path_map.items():
            if item.checkState(0) == Qt.Checked:
                selected.append(file_path)
        return selected

    def get_selected_count(self) -> int:
        return len(self.get_selected_files())

    def select_all(self, select: bool = True) -> None:
        root = self.invisibleRootItem()
        self._set_children_checked(root, select)
        self._update_all_parent_states()

    def _set_children_checked(self, item: QTreeWidgetItem, checked: bool) -> None:
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            self._set_children_checked(child, checked)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
        if item.childCount() > 0:
            checked = item.checkState(0) == Qt.Checked
            self._set_children_checked(item, checked)
        # Only update parent state incrementally (don't walk entire tree)
        self._update_parent_state(item)
        root = self.invisibleRootItem()
        if root.childCount() > 0:
            root_item = root.child(0)
            if root_item and root_item != item:
                # Only update root if this item is a direct child
                if item.parent() == root_item:
                    self._update_root_item_state(root_item)
        self.selection_changed.emit()

    def _update_item_state_from_children(self, item: QTreeWidgetItem) -> None:
        """Update an item's checkbox state based on its children's states.

        This is used to ensure folders show the correct state (checked/unchecked/partially checked)
        based on their children, even when collapsed. Recursively checks all descendants to handle
        collapsed subfolders correctly.
        """
        if item.childCount() == 0:
            return

        # Recursively check all descendants to find selected/unselected files
        # This is important when folders are collapsed - we need to check nested children too
        def count_selected_files(subtree_item: QTreeWidgetItem) -> tuple[int, int]:
            """Count selected and total files in this subtree.

            Returns:
                Tuple of (selected_count, total_count)
            """
            selected = 0
            total = 0

            # If this is a file, count it
            if subtree_item in self._file_path_map:
                total = 1
                if subtree_item.checkState(0) == Qt.Checked:
                    selected = 1
                return selected, total

            # If this is a folder, recursively check all children
            for i in range(subtree_item.childCount()):
                child = subtree_item.child(i)
                child_selected, child_total = count_selected_files(child)
                selected += child_selected
                total += child_total

            return selected, total

        # Count selected files in this item's subtree
        selected_count, total_count = count_selected_files(item)

        self.blockSignals(True)
        if total_count == 0:
            # No files in this subtree, keep current state or set to unchecked
            item.setCheckState(0, Qt.Unchecked)
        elif selected_count == total_count:
            # All files selected
            item.setCheckState(0, Qt.Checked)
        elif selected_count == 0:
            # No files selected
            item.setCheckState(0, Qt.Unchecked)
        else:
            # Mixed state - some files selected, some not
            item.setCheckState(0, Qt.PartiallyChecked)
        self.blockSignals(False)

    def _update_parent_state(self, item: QTreeWidgetItem) -> None:
        parent = item.parent()
        if parent is None:
            return
        checked_count = 0
        unchecked_count = 0
        for i in range(parent.childCount()):
            child = parent.child(i)
            state = child.checkState(0)
            if state == Qt.Checked:
                checked_count += 1
            elif state == Qt.Unchecked:
                unchecked_count += 1
        total = parent.childCount()
        self.blockSignals(True)
        if checked_count == total:
            parent.setCheckState(0, Qt.Checked)
        elif unchecked_count == total:
            parent.setCheckState(0, Qt.Unchecked)
        else:
            parent.setCheckState(0, Qt.PartiallyChecked)
        self.blockSignals(False)
        self._update_parent_state(parent)

    def _update_all_parent_states(self) -> None:
        """Update all parent states - optimized to only update items that have children.

        Uses _update_item_state_from_children to properly handle collapsed folders
        and show PartiallyChecked state when files inside are selected.
        """

        def update_item(item: QTreeWidgetItem):
            # Only process items that have children (folders)
            if item.childCount() > 0:
                # Process children first
                for i in range(item.childCount()):
                    update_item(item.child(i))
                # Then update this item's state based on all its children (including collapsed ones)
                self._update_item_state_from_children(item)

        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            update_item(root.child(i))

    def _update_root_item_state(self, root_item: QTreeWidgetItem) -> None:
        """Update root item state based on all its children, including collapsed ones."""
        if root_item.childCount() == 0:
            return
        # Use the recursive method to properly handle collapsed folders
        self._update_item_state_from_children(root_item)

    # --- CHANGED: Icon handling for Expand/Collapse ---
    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Update folder icon to opened state and ensure checkbox states are correct."""
        # Check if this is a locked directory - prevent expansion
        for locked_dir, locked_item in self._directory_item_map.items():
            if item == locked_item:
                # Collapse it immediately
                item.setExpanded(False)
                return

        # Check if it's a folder (has children or is root)
        # Note: We rely on the text to find the folder name
        if item.childCount() > 0 or item == self.topLevelItem(0):
            item.setIcon(0, get_folder_icon(item.text(0), is_open=True))

        # Update this item's state based on its children when expanded
        # This ensures checkboxes are shown correctly when the folder is expanded
        if item.childCount() > 0:
            self._update_item_state_from_children(item)

    def _on_item_collapsed(self, item: QTreeWidgetItem) -> None:
        """Update folder icon to closed state and ensure parent checkbox state is correct.

        Note: Child item checkStates are automatically preserved by Qt when collapsing.
        We update the parent state to ensure the dash (PartiallyChecked) is shown
        when children are selected but the folder is collapsed.
        """
        if item.childCount() > 0 or item == self.topLevelItem(0):
            item.setIcon(0, get_folder_icon(item.text(0), is_open=False))

        # Update this item's own state based on its children (even if collapsed)
        # This ensures the dash is shown when children are selected
        if item.childCount() > 0:
            self._update_item_state_from_children(item)

        # Update parent state to reflect this item's state
        self._update_parent_state(item)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle single click on tree items - expand/collapse folders."""
        # Only expand/collapse if it's a folder (has children) and not a file
        if item.childCount() > 0 and item not in self._file_path_map:
            # Toggle expanded state
            item.setExpanded(not item.isExpanded())

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double click on tree items - open files in editor."""
        if item in self._file_path_map:
            file_path = self._file_path_map[item]
            open_file_in_editor(file_path)
