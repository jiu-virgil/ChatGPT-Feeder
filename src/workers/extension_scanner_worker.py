"""Worker thread for scanning directory extensions asynchronously."""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.utils.file_scanner import scan_all_extensions


class ExtensionScannerWorker(QThread):
    """Worker thread for scanning directory extensions asynchronously."""

    finished = Signal(list)  # Emits list[str] of extensions

    def __init__(self, directory: Path, use_standard_filters: bool = True):
        super().__init__()
        self.directory = directory
        self.use_standard_filters = use_standard_filters

    def run(self):
        """Run the extension scan in background thread."""
        try:
            extensions = scan_all_extensions(
                self.directory, use_standard_filters=self.use_standard_filters
            )
            self.finished.emit(extensions)
        except Exception:
            # On any error, emit empty list
            self.finished.emit([])
