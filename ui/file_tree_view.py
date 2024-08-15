from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from pathlib import Path
import os
from ui.ui_helpers import refresh_tree_view


class CheckableTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, texts, parent=None):
        super().__init__(parent)
        self.setText(0, texts[0])  # Set text for the first column
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
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
        self.folder_icon = self._load_icon("resources/folder_icon.png")
        self.file_icon = self._load_icon("resources/code_icon.png")
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
        if self.file_icon:
            file_item.setIcon(0, self.file_icon)
        file_item.setCheckState(
            0, Qt.Checked if file_path in self.selected_files else Qt.Unchecked
        )
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
        (
            folder_item.setIcon(0, self.folder_icon)
            if self.folder_icon
            else folder_item.setText(0, f"📁 {part}")
        )
        (
            parent_item.addChild(folder_item)
            if parent_item
            else self.addTopLevelItem(folder_item)
        )
        return folder_item

    def get_selected_files(self):
        """Collect and return all selected files."""
        selected_files = set()
        root = self.invisibleRootItem()
        self._collect_selected_files_recursive(root, selected_files)
        return selected_files

    def _collect_selected_files_recursive(self, item, selected_files):
        """Recursively collect all selected files from the tree."""
        for i in range(item.childCount()):
            child = item.child(i)
            # If the child is a file and is checked, add it to the selected files set
            if child.checkState(0) == Qt.Checked and child.childCount() == 0:
                # Extract the full path of the file by walking up the parent hierarchy
                file_path = Path(self._get_full_path(child))
                selected_files.add(file_path)
            # Recursively check children (subfolders/files)
            self._collect_selected_files_recursive(child, selected_files)

    def _get_full_path(self, item):
        """Reconstruct the full file path from the tree hierarchy."""
        parts = []
        while item is not None:
            parts.append(item.text(0).split(" ", 1)[-1])  # Strip out emoji if present
            item = item.parent()
        return os.path.join(*reversed(parts))

    def select_folder_children(self, item):
        """Select all children when a folder is selected."""
        select = item.checkState(0) == Qt.Checked
        self._select_all_recursive(item, select)
        refresh_tree_view(self)

    def _select_all_recursive(self, item, select):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, Qt.Checked if select else Qt.Unchecked)
            self._select_all_recursive(child, select)

    def _are_all_children_checked(self, item):
        """Recursively check if all children of an item are checked."""
        for i in range(item.childCount()):
            child = item.child(i)
            if child.checkState(0) != Qt.Checked:
                return False
            if not self._are_all_children_checked(child):
                return False
        return True

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
