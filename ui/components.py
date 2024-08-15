from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt


class CheckableTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, texts, parent=None):
        # Initialize QTreeWidgetItem with proper arguments
        super().__init__(parent)
        self.setText(0, texts[0])  # Set text for the first column
        self.setFlags(
            self.flags() | Qt.ItemIsUserCheckable
        )  # Allow user checkable items
        self.setCheckState(0, Qt.Unchecked)  # Default to unchecked

        # If multiple texts are passed, set them for the other columns
        for i, text in enumerate(texts[1:], start=1):
            self.setText(i, text)
