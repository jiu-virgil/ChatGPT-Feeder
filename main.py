from PySide6.QtWidgets import QApplication
from ui.file_selector_ui import FileSelectorUI
from utils.file_helpers import (
    find_python_files,
    load_app_state,
)  # Import the correct function


def main():
    app = QApplication([])

    python_files = find_python_files()
    app_state = load_app_state()  # Load the full app state

    window = FileSelectorUI(python_files, app_state)  # Pass app_state to the window
    window.show()

    app.exec()


if __name__ == "__main__":
    main()
