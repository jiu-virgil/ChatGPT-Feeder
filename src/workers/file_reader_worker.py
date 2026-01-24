"""Worker thread for reading file contents asynchronously."""
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.utils.file_reader import read_file_content


class FileReaderWorker(QThread):
    """Worker thread for reading file contents asynchronously."""
    
    finished = Signal(dict)  # Emits content_map: dict[str, str]
    
    def __init__(self, file_paths: list[Path], cache: dict[str, str]):
        super().__init__()
        self.file_paths = file_paths
        self.cache = cache
    
    def run(self):
        """Read file contents in background thread."""
        content_map = {}
        for file_path in self.file_paths:
            path_str = str(file_path)
            # Check cache first
            if path_str in self.cache:
                content_map[path_str] = self.cache[path_str]
            else:
                # Read and cache
                content = read_file_content(file_path)
                content_map[path_str] = content
                self.cache[path_str] = content
        self.finished.emit(content_map)


