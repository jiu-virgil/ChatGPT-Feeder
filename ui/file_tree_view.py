from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from pathlib import Path
import os


class CheckableTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, texts, parent=None):
        super().__init__(parent)
        self.setText(0, texts[0])  # Set text for the first column
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        self.setCheckState(0, Qt.Unchecked)
        for i, text in enumerate(texts[1:], start=1):
            self.setText(i, text)


class FileTreeView(QTreeWidget):
    def __init__(self, python_files, extension, selected_files):
        super().__init__()
        self.setHeaderHidden(True)
        self.python_files = python_files
        self.extension = extension
        self.selected_files = selected_files

        # Load icons or fall back to emojis
        self.folder_icon = self._load_icon("resources/folder_icon.png") or "📁"
        self.expanded_folder_icon = (
            self._load_icon("resources/expanded_folder_icon.png") or "📂"
        )
        self.file_icon = self._load_icon("resources/file_icon.png") or "📄"

        # Connect signals
        self.itemExpanded.connect(self.handle_item_expanded)
        self.itemCollapsed.connect(self.handle_item_collapsed)
        self.itemDoubleClicked.connect(self.handle_item_double_clicked)

        self.populate_tree()
        self.expandAll()

    def _load_icon(self, path):
        return QIcon(path) if os.path.exists(path) else None

    def update_extension(self, extension):
        """Update the file extension filter and repopulate the tree."""
        self.extension = extension
        self.populate_tree()
        self.expandAll()

    def populate_tree(self):
        """Populate the tree widget with files matching the selected extension."""
        self.clear()
        path_map = {}

        for file_path in self.python_files:
            if file_path.suffix == self.extension:
                self._add_file_to_tree(file_path, path_map)

    def _add_file_to_tree(self, file_path, path_map):
        parts = file_path.parts
        current_path = Path(parts[0])
        parent_item = self._create_or_get_parent_item(
            parts[:-1], current_path, path_map
        )

        file_item = CheckableTreeWidgetItem([parts[-1]], parent_item)
        if isinstance(self.file_icon, QIcon):
            file_item.setIcon(0, self.file_icon)
        else:
            file_item.setText(0, f"{self.file_icon} {parts[-1]}")

        (
            parent_item.addChild(file_item)
            if parent_item
            else self.addTopLevelItem(file_item)
        )

    def _create_or_get_parent_item(self, parts, current_path, path_map):
        parent_item = None
        for part in parts:
            if current_path not in path_map:
                parent_item = self._create_folder_item(part, parent_item)
                path_map[current_path] = parent_item
            else:
                parent_item = path_map[current_path]
            current_path = current_path / part
        return parent_item

    def _create_folder_item(self, part, parent_item):
        folder_item = CheckableTreeWidgetItem([part], parent_item)
        if isinstance(self.folder_icon, QIcon):
            folder_item.setIcon(0, self.folder_icon)
        else:
            folder_item.setText(0, f"{self.folder_icon} {part}")

        (
            parent_item.addChild(folder_item)
            if parent_item
            else self.addTopLevelItem(folder_item)
        )
        return folder_item

    def are_all_items_checked(self):
        """Check if all items in the tree are checked."""
        root = self.invisibleRootItem()
        return self._are_all_children_checked(root)

    def _are_all_children_checked(self, item):
        """Recursively check if all children of an item are checked."""
        for i in range(item.childCount()):
            child = item.child(i)
            if child.checkState(0) != Qt.Checked:
                return False
            if not self._are_all_children_checked(child):
                return False
        return True

    def are_all_items_unchecked(self):
        """Check if all items in the tree are unchecked."""
        root = self.invisibleRootItem()
        return self._are_all_children_unchecked(root)

    def _are_all_children_unchecked(self, item):
        """Recursively check if all children of an item are unchecked."""
        for i in range(item.childCount()):
            child = item.child(i)
            if child.checkState(0) != Qt.Unchecked:
                return False
            if not self._are_all_children_unchecked(child):
                return False
        return True

    def handle_item_expanded(self, item):
        """Handle the folder being expanded to toggle the icon."""
        if item.childCount() > 0:  # It's a folder
            if isinstance(self.expanded_folder_icon, QIcon):
                item.setIcon(0, self.expanded_folder_icon)
            else:
                item.setText(
                    0, f"📂 {item.text(0)[2:]}"
                )  # Replace the first two chars (emoji + space)

    def handle_item_collapsed(self, item):
        """Handle the folder being collapsed to toggle the icon."""
        if item.childCount() > 0:  # It's a folder
            if isinstance(self.folder_icon, QIcon):
                item.setIcon(0, self.folder_icon)
            else:
                item.setText(
                    0, f"📁 {item.text(0)[2:]}"
                )  # Replace the first two chars (emoji + space)

    def select_folder_children(self, item):
        """Select or deselect all children when a folder is selected or deselected."""
        select = item.checkState(0) == Qt.Checked
        self.blockSignals(True)  # Block signals to prevent recursion
        self._select_all_recursive(item, select)
        self.blockSignals(False)  # Unblock signals after update

    def _select_all_recursive(self, item, select):
        """Recursively select or deselect all children of an item."""
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, Qt.Checked if select else Qt.Unchecked)
            self._select_all_recursive(child, select)

    def update_parent_check_state(self, item):
        """Recursively update the state of parent items based on the state of their children."""
        parent = item.parent()
        if parent is None:
            return

        all_checked = True
        all_unchecked = True

        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.checkState(0) != Qt.Checked:
                all_checked = False
            if child.checkState(0) != Qt.Unchecked:
                all_unchecked = False

        self.blockSignals(True)  # Block signals to prevent recursion
        if all_checked:
            parent.setCheckState(0, Qt.Checked)
        elif all_unchecked:
            parent.setCheckState(0, Qt.Unchecked)
        else:
            parent.setCheckState(0, Qt.PartiallyChecked)
        self.blockSignals(False)  # Unblock signals after update

        # Recursively update the parent's state
        self.update_parent_check_state(parent)

    def on_item_changed(self, item):
        """Handle item state change and update parent and children."""
        if item.childCount() > 0:
            # Update all children based on the folder's state (checked or unchecked)
            self.select_folder_children(item)
        self.update_parent_check_state(item)

    def handle_item_double_clicked(self, item, column):
        """Open the file in the default editor when double-clicked."""
        if item.childCount() == 0:  # Only open if it's a file (no children)
            file_path = self._get_full_path(item)
            if os.path.isfile(file_path):
                self.open_file_in_default_editor(file_path)

    def _get_full_path(self, item):
        """Reconstruct the full file path from the tree hierarchy."""
        parts = []
        while item is not None:
            parts.append(item.text(0).split(" ", 1)[-1])  # Strip out emoji if present
            item = item.parent()
        return os.path.join(*reversed(parts))

    def open_file_in_default_editor(self, file_path):
        """Open the specified file in the default system editor."""
        try:
            if os.name == "nt":  # Windows
                os.startfile(file_path)
            elif os.name == "posix":  # macOS or Linux
                subprocess.run(
                    ["open", file_path]
                    if sys.platform == "darwin"
                    else ["xdg-open", file_path]
                )
        except Exception as e:
            print(f"Failed to open {file_path}: {e}")
