from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from ui.file_extension_input import FileExtensionInput
from ui.file_tree_view import FileTreeView
from utils.file_helpers import save_last_selection, collect_file_data, copy_to_clipboard
from ui.ui_helpers import (
    toggle_all_tree_items,
    setup_main_layout,
    create_submit_button,
    create_select_all_checkbox,
)


class FileSelectorUI(QMainWindow):

    def __init__(self, python_files, last_selection):
        super().__init__()
        self.setWindowTitle(" Spoon App")
        self.setWindowIcon(QIcon("resources/spoon.png"))
        self.setGeometry(100, 100, 600, 400)

        self.resize(400, 600)

        self.selected_files = set(last_selection)

        # Main layout
        main_layout = QVBoxLayout()

        # File extension input with lock
        self.file_extension_input = FileExtensionInput(".py", self.update_file_filter)
        self.select_all_checkbox = create_select_all_checkbox(
            self.file_extension_input, self.toggle_select_all_files
        )
        self.tree_view = FileTreeView(
            python_files, self.file_extension_input.get_extension(), last_selection
        )
        self.tree_view.itemChanged.connect(self.on_item_changed)

        # Buttons for expanding and collapsing the tree
        button_layout = QHBoxLayout()
        expand_button = QPushButton("➕ Expand All")
        expand_button.clicked.connect(self.expand_all)
        collapse_button = QPushButton("➖ Collapse All")
        collapse_button.clicked.connect(self.collapse_all)

        button_layout.addWidget(expand_button)
        button_layout.addWidget(collapse_button)
        main_layout.addLayout(button_layout)

        submit_button = create_submit_button(self.on_submit)

        setup_main_layout(
            main_layout,
            self.file_extension_input,
            self.select_all_checkbox,
            self.tree_view,
            submit_button,
        )

        # Set main widget and layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Ensure all items are selected initially and update checkbox state
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
        self.selected_files = self.tree_view.get_selected_files()

        if self.selected_files:
            save_last_selection(self.selected_files)
            collected_data = collect_file_data(self.selected_files)
            formatted_data = "\n\n".join(
                f"# {title}\n{content}" for title, content in collected_data.items()
            )
            copy_to_clipboard(formatted_data)

    def update_file_filter(self):
        """Update the tree view based on the file extension input."""
        extension = self.file_extension_input.get_extension()
        self.tree_view.update_extension(extension)

        # Ensure that the "Select All" checkbox reflects the correct state after filtering
        self.update_select_all_checkbox()

        # If the "Select All" checkbox is checked, ensure that all items in the tree are checked
        if self.select_all_checkbox.isChecked():
            self.toggle_select_all_files()

    def toggle_select_all_files(self, initial=False):
        """Select/deselect all files in the tree view and focus the tree."""
        select_all = initial or self.select_all_checkbox.isChecked()
        toggle_all_tree_items(self.tree_view, select_all)

        # Focus the tree view when the select all checkbox is interacted with
        self.tree_view.setFocus()

        # Ensure the checkbox reflects the correct state
        self.update_select_all_checkbox()

    def on_item_changed(self, item):
        """Handle item state change to select/deselect children for folders."""
        if item.childCount() > 0:  # If it's a folder
            self.tree_view.select_folder_children(item)

        # After changing the state of an item, update the select all checkbox
        self.update_select_all_checkbox()

    def update_select_all_checkbox(self):
        """Update the state of the select all checkbox based on tree view items."""
        all_items_checked = self.tree_view.are_all_items_checked()
        any_items_checked = not self.tree_view.are_all_items_unchecked()

        # Block signals to prevent infinite loops when setting the checkbox state
        self.select_all_checkbox.blockSignals(True)

        if all_items_checked:
            self.select_all_checkbox.setCheckState(Qt.Checked)
        elif any_items_checked:
            self.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
        else:
            self.select_all_checkbox.setCheckState(Qt.Unchecked)

        self.select_all_checkbox.blockSignals(False)
