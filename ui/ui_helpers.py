from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QCheckBox
from PySide6.QtGui import QFont


def toggle_all_tree_items(tree_widget, select_all):
    """Toggle the selection state of all items in a tree view."""
    root = tree_widget.invisibleRootItem()
    _select_all_recursive(root, select_all)
    refresh_tree_view(tree_widget)


def _select_all_recursive(item, select):
    """Recursively select/deselect all children of an item."""
    for i in range(item.childCount()):
        child = item.child(i)
        child.setCheckState(0, Qt.Checked if select else Qt.Unchecked)
        _select_all_recursive(child, select)


def refresh_tree_view(tree_widget):
    """Force the tree view to refresh and repaint."""
    tree_widget.viewport().update()  # Update the visible portion of the widget
    tree_widget.repaint()  # Repaint the widget


def setup_main_layout(
    main_layout, file_extension_input, select_all_checkbox, tree_view, submit_button
):
    """Set up the main layout with the provided widgets."""
    main_layout.addLayout(file_extension_input.layout)
    main_layout.addWidget(select_all_checkbox)
    main_layout.addWidget(tree_view)
    main_layout.addWidget(submit_button)


def create_submit_button(on_submit_callback):
    """Create a submit button and set up its properties."""
    submit_button = QPushButton("Submit")

    # Correct way to set font: Create a QFont object with font name and size
    submit_button.setFont(QFont("Arial", 12))  # Set font name and size

    submit_button.setFixedHeight(50)  # Larger height for the button
    submit_button.clicked.connect(on_submit_callback)
    return submit_button


def create_select_all_checkbox(file_extension_input, toggle_select_all_files_callback):
    """Create a 'Select All' checkbox and connect its state change event."""
    select_all_checkbox = QCheckBox(
        f"Select all {file_extension_input.get_extension()} files"
    )
    select_all_checkbox.stateChanged.connect(toggle_select_all_files_callback)
    return select_all_checkbox


