"""Application entry point."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from src.config import STYLES_PATH, APP_NAME
from src.components.main_window import MainWindow


def create_app() -> QApplication:
    """Create and configure the QApplication."""
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    
    # Load stylesheet
    if STYLES_PATH.exists():
        with open(STYLES_PATH, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    
    return app


def main() -> int:
    """Main entry point."""
    app = create_app()
    
    window = MainWindow()
    window.show()
    
    # Force window to front after a small delay to ensure it's fully shown
    def bring_to_front():
        window.raise_()
        window.activateWindow()
    
    QTimer.singleShot(50, bring_to_front)
    
    return app.exec()


