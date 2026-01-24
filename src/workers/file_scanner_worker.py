"""Worker thread for scanning directory files asynchronously."""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.utils.file_scanner import scan_files


class FileScannerWorker(QThread):
    """Worker thread for scanning directory files asynchronously."""

    finished = Signal(
        object
    )  # Emits scan result tuple: (files, file_count, directory_counts, extension_counts, error)

    def __init__(
        self,
        directory: Path,
        extension: str,
        check_limit: int | None = None,
        collect_extensions: bool = True,
        use_standard_filters: bool = True,
    ):
        super().__init__()
        self.directory = directory
        self.extension = extension
        self.check_limit = check_limit
        self.collect_extensions = collect_extensions
        self.use_standard_filters = use_standard_filters

    def run(self):
        """Run the file scan in background thread."""
        try:
            files, file_count, directory_counts, extension_counts = scan_files(
                self.directory,
                self.extension,
                check_limit=self.check_limit,
                collect_extensions=self.collect_extensions,
                use_standard_filters=self.use_standard_filters,
            )
            # Emit signal with results
            self.finished.emit(
                (files, file_count, directory_counts, extension_counts, None)
            )
        except Exception as e:
            import traceback

            print(f"Error in FileScannerWorker: {e}")
            traceback.print_exc()
            self.finished.emit(([], 0, {}, {}, str(e)))
