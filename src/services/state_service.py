"""State management service for application state and path conversions."""

from pathlib import Path

from src.state import add_recent_directory, load_state, save_state


class StateService:
    """Service for managing application state and path conversions."""

    def __init__(self):
        self._current_directory: Path | None = None

    def set_current_directory(self, directory: Path) -> None:
        """Set the current directory for path conversions."""
        self._current_directory = directory

    def get_current_directory(self) -> Path:
        """Get the current directory."""
        if self._current_directory is None:
            self._current_directory = Path.cwd()
        return self._current_directory

    def paths_to_state_tuples(self, paths: list[Path]) -> set[tuple[str, str]]:
        """Convert Path objects to state tuples relative to current directory.

        Args:
            paths: List of file paths to convert

        Returns:
            Set of tuples (directory_path, filename)
        """
        selected_tuples = set()
        current_dir = self.get_current_directory()

        for path in paths:
            try:
                rel_path = path.relative_to(current_dir)
                if len(rel_path.parts) >= 2:
                    selected_tuples.add((str(rel_path.parent), rel_path.name))
                else:
                    selected_tuples.add((".", rel_path.name))
            except ValueError:
                # Path is not relative to current directory, use absolute
                selected_tuples.add((str(path.parent), path.name))

        return selected_tuples

    def state_tuples_to_paths(self, state_tuples: set[tuple[str, str]]) -> set[Path]:
        """Convert state tuples to Path objects relative to current directory.

        Args:
            state_tuples: Set of tuples (directory_path, filename)

        Returns:
            Set of Path objects
        """
        selected_paths = set()
        current_dir = self.get_current_directory()

        for file_tuple in state_tuples:
            if len(file_tuple) == 2:
                selected_paths.add(current_dir / file_tuple[0] / file_tuple[1])

        return selected_paths

    def get_selected_paths_from_state(self) -> set[Path]:
        """Get selected file paths from saved state.

        Returns:
            Set of Path objects for selected files
        """
        state = load_state()
        state_tuples = state.get("selected_files", set())
        return self.state_tuples_to_paths(state_tuples)

    def load_state(self) -> dict:
        """Load application state.

        Returns:
            Dictionary containing application state
        """
        return load_state()

    def save_state(
        self,
        selected_files: set[tuple[str, str]],
        select_all_state: bool,
        recent_directories: list[str] | None = None,
    ) -> bool:
        """Save application state.

        Args:
            selected_files: Set of tuples (directory_path, filename)
            select_all_state: Whether all files were selected
            recent_directories: List of recent directory paths

        Returns:
            True if save was successful, False otherwise
        """
        return save_state(selected_files, select_all_state, recent_directories)

    def add_recent_directory(
        self, directories: list[str], new_directory: str
    ) -> list[str]:
        """Add a directory to recent directories list.

        Args:
            directories: Current list of recent directories
            new_directory: New directory to add

        Returns:
            Updated list of recent directories
        """
        return add_recent_directory(directories, new_directory)
