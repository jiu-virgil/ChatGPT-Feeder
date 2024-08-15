from PySide6.QtWidgets import QApplication
from ui.file_selector_ui import FileSelectorUI
from utils.file_helpers import find_python_files, load_last_selection


def main():
    app = QApplication([])

    python_files = find_python_files()
    last_selection = load_last_selection()

    window = FileSelectorUI(python_files, last_selection)
    window.show()

    app.exec()


if __name__ == "__main__":
    main()
