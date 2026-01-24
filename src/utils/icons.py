"""File type icon utilities using VS Code Icons."""

import os
from pathlib import Path
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from src.config import ICONS_DIR

# Debug mode - set SPOON_DEBUG_ICONS=1 to enable verbose icon loading logs
DEBUG_ICONS = os.getenv("SPOON_DEBUG_ICONS", "0") == "1"


def _debug_print(*args, **kwargs):
    """Print debug messages only if debug mode is enabled."""
    if DEBUG_ICONS:
        print(*args, **kwargs)


# 1. Import Manifest
try:
    from src.utils.icon_manifest import AVAILABLE_ICONS  # type: ignore
except ImportError:
    AVAILABLE_ICONS = None

# 2. Map Extensions to the "Curated" list
EXTENSION_ICON_MAP: Final[dict[str, str]] = {
    # Code
    ".py": "file_type_python.svg",
    ".js": "file_type_js.svg",
    ".ts": "file_type_typescript.svg",
    ".jsx": "file_type_reactjs.svg",
    ".tsx": "file_type_reactts.svg",
    ".html": "file_type_html.svg",
    ".css": "file_type_css.svg",
    ".scss": "file_type_scss.svg",
    ".c": "file_type_c.svg",
    ".h": "file_type_c.svg",
    ".cpp": "file_type_cpp.svg",
    ".cs": "file_type_csharp.svg",
    ".java": "file_type_java.svg",
    ".go": "file_type_go.svg",
    ".rs": "file_type_rust.svg",
    ".php": "file_type_php.svg",
    ".rb": "file_type_ruby.svg",
    # Data / Config
    ".json": "file_type_json.svg",
    ".yaml": "file_type_yaml.svg",
    ".yml": "file_type_yaml.svg",
    ".xml": "file_type_xml.svg",
    ".md": "file_type_markdown.svg",
    ".txt": "file_type_text.svg",
    ".log": "file_type_log.svg",
    ".ini": "file_type_settings.svg",
    ".env": "file_type_env.svg",
    ".gitignore": "file_type_git.svg",
    ".dockerfile": "file_type_docker.svg",
    # Archives / Exec
    ".zip": "file_type_zip.svg",
    ".pdf": "file_type_pdf.svg",
    ".exe": "file_type_exe.svg",
}


class IconManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._icon_cache: dict[str, QIcon] = {}
        self._available_icon_files: set[str] = set()

        # Debug: Show icon directory path
        _debug_print(f"IconManager: ICONS_DIR = {ICONS_DIR}")
        _debug_print(f"IconManager: ICONS_DIR exists = {ICONS_DIR.exists()}")
        _debug_print(f"IconManager: ICONS_DIR resolved = {ICONS_DIR.resolve()}")

        if AVAILABLE_ICONS and isinstance(AVAILABLE_ICONS, set):
            self._available_icon_files = AVAILABLE_ICONS
            _debug_print(
                f"IconManager: Loaded {len(self._available_icon_files)} icon(s) from manifest"
            )
        else:
            _debug_print("IconManager: Manifest not available, scanning directory...")
            self._scan_icons_dir()
            _debug_print(
                f"IconManager: Found {len(self._available_icon_files)} icon(s) after scanning"
            )

        self._initialized = True

    def _scan_icons_dir(self) -> None:
        """Scan the icons directory for available SVG files."""
        if not ICONS_DIR.exists():
            print(f"Warning: Icons directory does not exist: {ICONS_DIR}")
            _debug_print(f"  Resolved path: {ICONS_DIR.resolve()}")
            _debug_print(f"  Current working directory: {Path.cwd()}")
            return

        try:
            count = 0
            with os.scandir(ICONS_DIR) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.endswith(".svg"):
                        self._available_icon_files.add(entry.name)
                        count += 1
            if count > 0:
                _debug_print(f"Loaded {count} icon(s) from {ICONS_DIR}")
            else:
                print(f"Warning: No SVG files found in {ICONS_DIR}")
        except PermissionError as e:
            print(f"Error: Permission denied scanning icons directory: {ICONS_DIR}")
            print(f"  {e}")
        except Exception as e:
            print(f"Error scanning icons directory {ICONS_DIR}: {e}")
            if DEBUG_ICONS:
                import traceback

                traceback.print_exc()

    def _load_icon(self, filename: str) -> QIcon:
        if filename in self._icon_cache:
            return self._icon_cache[filename]

        path = ICONS_DIR / filename
        if path.exists():
            try:
                # Try loading SVG using QSvgRenderer (more reliable for SVG files)
                if filename.endswith(".svg"):
                    renderer = QSvgRenderer(str(path.resolve()))
                    if renderer.isValid():
                        # Create a pixmap with transparent background
                        pixmap = QPixmap(16, 16)
                        pixmap.fill(Qt.transparent)  # Transparent background
                        painter = QPainter(pixmap)
                        painter.setRenderHint(QPainter.Antialiasing)
                        renderer.render(painter)
                        painter.end()
                        icon = QIcon(pixmap)
                        if not icon.isNull():
                            self._icon_cache[filename] = icon
                            return icon
                    # Fallback to direct QIcon if renderer fails
                    _debug_print(
                        f"Warning: QSvgRenderer failed for {filename}, trying QIcon directly"
                    )

                # Try direct QIcon loading (works for some formats)
                icon = QIcon(str(path.resolve()))
                if not icon.isNull():
                    self._icon_cache[filename] = icon
                    return icon
                else:
                    _debug_print(
                        f"Warning: Failed to load icon {filename} from {path} (icon is null)"
                    )
            except Exception as e:
                print(f"Error loading icon {filename} from {path}: {e}")
                if DEBUG_ICONS:
                    import traceback

                    traceback.print_exc()
        else:
            _debug_print(f"Warning: Icon file not found: {path}")

        # Return empty icon as fallback
        empty = QIcon()
        self._icon_cache[filename] = empty
        return empty

    def get_file_icon(self, extension: str) -> QIcon:
        ext = extension.strip().lower()
        if not ext.startswith("."):
            ext = "." + ext

        # 1. Exact Map
        if ext in EXTENSION_ICON_MAP:
            return self._load_icon(EXTENSION_ICON_MAP[ext])

        # 2. Try generic match
        # e.g., .lua -> file_type_lua.svg
        clean_ext = ext.lstrip(".")
        candidate = f"file_type_{clean_ext}.svg"
        if candidate in self._available_icon_files:
            return self._load_icon(candidate)

        return self._load_icon("default_file.svg")

    def get_folder_icon(self, folder_name: str, is_open: bool = False) -> QIcon:
        name = folder_name.lower()
        suffix = "_opened.svg" if is_open else ".svg"

        # 1. Try specific folder (e.g., folder_type_src.svg)
        candidate = f"folder_type_{name}{suffix}"
        if candidate in self._available_icon_files:
            return self._load_icon(candidate)

        # 2. Handle dot folders (.git, .vscode)
        if name.startswith("."):
            clean = name.lstrip(".")
            candidate = f"folder_type_{clean}{suffix}"
            if candidate in self._available_icon_files:
                return self._load_icon(candidate)

        # 3. Default
        default = "default_folder_opened.svg" if is_open else "default_folder.svg"
        return self._load_icon(default)


_manager = IconManager()


def get_icon_for_extension(extension: str) -> QIcon:
    return _manager.get_file_icon(extension)


def get_folder_icon(folder_name: str, is_open: bool = False) -> QIcon:
    return _manager.get_folder_icon(folder_name, is_open)


def get_ui_icon(icon_name: str) -> QIcon:
    """Get UI icon by name (e.g., 'folder', 'search', 'expand', 'collapse', 'lock').

    Args:
        icon_name: Name of the UI icon

    Returns:
        QIcon for the requested UI element, or empty icon if not found
    """
    # Map common UI icon names to VSCode icon filenames
    ui_icon_map = {
        "folder": "default_folder_opened.svg",
        "folder-open": "default_folder_opened.svg",
        "search": "search.svg",
        "expand": "chevron-down.svg",
        "collapse": "chevron-up.svg",
        "lock": "lock.svg",
        "loading": "loading.svg",
        "check": "check.svg",
        "warning": "warning.svg",
        "error": "error.svg",
        "copy": "copy.svg",
    }

    # Try mapped name first
    if icon_name in ui_icon_map:
        icon_file = ui_icon_map[icon_name]
        icon = _manager._load_icon(icon_file)
        if not icon.isNull():
            return icon

    # Try direct name
    if icon_name.endswith(".svg"):
        return _manager._load_icon(icon_name)
    else:
        return _manager._load_icon(f"{icon_name}.svg")
