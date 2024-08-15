from PySide6.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt, QSize


class FileExtensionInput:
    def __init__(self, default_extension, on_update_callback):
        self.extension = default_extension
        self.is_locked = True  # Start with the extension locked
        self.on_update_callback = on_update_callback

        # Vertical layout for the label and input components
        self.layout = QVBoxLayout()

        # Label for file extension input
        self.label = QLabel("File extension:")
        self.layout.addWidget(self.label)

        # Horizontal layout for the lock icon and input
        input_layout = QHBoxLayout()

        # Lock/Unlock icon button
        self.lock_button = QPushButton("🔒")  # Locked by default
        self.lock_button.setFixedSize(QSize(24, 24))  # Size similar to a checkbox
        self.lock_button.clicked.connect(self.toggle_lock)
        input_layout.addWidget(self.lock_button)

        # File extension input
        self.input = QLineEdit(self.extension)
        self.input.setFixedWidth(100)  # Adjust width to accommodate more characters
        self.input.setAlignment(Qt.AlignLeft)  # Align the input to the left
        self.input.returnPressed.connect(self.handle_enter_press)  # Lock on Enter press
        self.set_input_locked_appearance()  # Set appearance based on lock state
        input_layout.addWidget(self.input)

        # Ensure the input is aligned to the left
        input_layout.addStretch()

        self.layout.addLayout(input_layout)

    def set_input_locked_appearance(self):
        """Set the visual appearance of the input to indicate it's locked."""
        palette = self.input.palette()
        app_palette = (
            self.input.style().standardPalette()
        )  # Get the application's standard palette

        # Get the main window's background color
        main_window_palette = self.input.window().palette()
        main_window_bg_color = main_window_palette.color(QPalette.Window)

        # Get the lock button's background color
        button_palette = self.lock_button.palette()
        button_bg_color = button_palette.color(QPalette.Button)

        if self.is_locked:
            # Locked state: Use main window's background color for the input field
            palette.setColor(QPalette.Base, main_window_bg_color)  # Background color
            palette.setColor(
                QPalette.Text, app_palette.color(QPalette.Disabled, QPalette.Text)
            )  # Text color
            self.input.setPalette(palette)
            self.input.setEnabled(False)  # Disable input
        else:
            # Unlocked state: Use lock button's background color for the input field
            palette.setColor(QPalette.Base, button_bg_color)  # Background color
            palette.setColor(QPalette.Text, Qt.white)
            self.input.setPalette(palette)
            self.input.setEnabled(True)  # Enable input

    def handle_enter_press(self):
        """Lock the input field when Enter is pressed."""
        if not self.is_locked:  # Only lock if it's currently unlocked
            self.toggle_lock()

    def toggle_lock(self):
        """Toggle the lock state of the file extension input."""
        self.is_locked = not self.is_locked
        self.set_input_locked_appearance()
        self.lock_button.setText("🔓" if not self.is_locked else "🔒")
        if self.is_locked:
            self.on_update_callback()  # Apply filter when locking

    def get_extension(self):
        """Return the current file extension."""
        return self.input.text().strip()
