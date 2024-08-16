from PySide6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QCheckBox,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from ui.file_extension_input import FileExtensionInput
from ui.file_tree_view import FileTreeView
from utils.file_helpers import (
    save_app_state,
    collect_file_data,
    copy_to_clipboard,
)
from utils.ui_helpers import toggle_all_tree_items


class FileSelectorUI(QMainWindow):
    def __init__(self, python_files, app_state):
        super().__init__()
        self.setWindowTitle("Spoon App")
        self.setWindowIcon(QIcon("resources/spoon.png"))
        self.setGeometry(100, 100, 600, 400)

        self.resize(400, 600)

        # Initialize the application state from app_state
        self.selected_files = set(app_state["selected_files"])
        self.select_all_state = app_state["select_all_state"]
        self.file_extension = app_state["file_extension"]

        # Main layout
        main_layout = QVBoxLayout()

        # File extension input with lock
        self.file_extension_input = FileExtensionInput(
            self.file_extension, self.update_file_filter
        )
        self.select_all_checkbox = QCheckBox(f"Select all {self.file_extension} files")
        self.select_all_checkbox.setChecked(self.select_all_state)
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all_files)

        self.tree_view = FileTreeView(
            python_files, self.file_extension, self.selected_files
        )
        self.tree_view.itemChanged.connect(self.tree_view.on_item_changed)

        # Buttons for expanding and collapsing the tree
        button_layout = QHBoxLayout()
        expand_button = QPushButton("➕ Expand All")
        expand_button.clicked.connect(self.expand_all)
        collapse_button = QPushButton("➖ Collapse All")
        collapse_button.clicked.connect(self.collapse_all)

        button_layout.addWidget(expand_button)
        button_layout.addWidget(collapse_button)
        main_layout.addLayout(button_layout)

        # Setup the layout with all widgets
        main_layout.addLayout(self.file_extension_input.layout)
        main_layout.addWidget(self.select_all_checkbox)
        main_layout.addWidget(self.tree_view)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Ensure the initial state is reflected in the UI
        self.toggle_select_all_files(initial=True)
        self.update_select_all_checkbox()

    def expand_all(self):
        """Expand all items in the tree view."""
        self.tree_view.expandAll()

    def collapse_all(self):
        """Collapse all items in the tree view."""
        self.tree_view.collapseAll()

    def on_submit(self):
        """Handle submit button click."""
        # Collect the selected files
        self.selected_files = self.tree_view.get_selected_files()

        if self.selected_files:
            # Save the application state, including selected files, "Select All" checkbox state, and file extension
            save_app_state(
                self.selected_files,
                self.select_all_checkbox.isChecked(),
                self.file_extension_input.get_extension(),
            )

            # Collect data from the selected files
            full_paths = {
                os.path.join(folder, filename)
                for folder, filename in self.selected_files
            }
            collected_data = collect_file_data(full_paths)

            # Format the collected data and copy to clipboard
            formatted_data = "\n\n".join(
                f"# {file_path}\n{content}"
                for file_path, content in collected_data.items()
            )
            copy_to_clipboard(formatted_data)

    def update_file_filter(self):
        """Update the tree view based on the file extension input."""
        extension = self.file_extension_input.get_extension()
        self.tree_view.update_extension(extension)
        self.update_select_all_checkbox()

        # Ensure all items are selected if the "Select All" checkbox is checked
        if self.select_all_checkbox.isChecked():
            self.toggle_select_all_files()

    def toggle_select_all_files(self, initial=False):
        """Select/deselect all files in the tree view and focus the tree."""
        select_all = initial or self.select_all_checkbox.isChecked()
        toggle_all_tree_items(self.tree_view, select_all)
        self.tree_view.setFocus()
        self.update_select_all_checkbox()

    def update_select_all_checkbox(self):
        """Update the state of the select all checkbox based on tree view items."""
        all_items_checked = self.tree_view.are_all_items_checked()
        any_items_checked = not self.tree_view.are_all_items_unchecked()

        self.select_all_checkbox.blockSignals(True)

        if all_items_checked:
            self.select_all_checkbox.setCheckState(Qt.Checked)
        elif any_items_checked:
            self.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
        else:
            self.select_all_checkbox.setCheckState(Qt.Unchecked)

        self.select_all_checkbox.blockSignals(False)
