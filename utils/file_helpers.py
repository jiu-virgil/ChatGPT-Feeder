import json
import os
import pickle
from pathlib import Path
import pyperclip

# Constants
PICKLE_FILE = ".last_selection.pickle"
IGNORE_FILE = ".gitignore"


def get_ignored_patterns():
    """Reads the .gitignore file and returns a list of ignored patterns."""
    ignore_patterns = []
    if Path(IGNORE_FILE).exists():
        with open(IGNORE_FILE, "r") as f:
            ignore_patterns = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    return ignore_patterns


def is_ignored(file_path, ignore_patterns):
    """Checks if a file matches any of the ignore patterns."""
    for pattern in ignore_patterns:
        if file_path.match(pattern) or file_path.is_relative_to(pattern):
            return True
    return False


def find_python_files():
    """Find all Python files in the project, excluding ignored files and directories."""
    ignore_patterns = get_ignored_patterns()
    python_files = []
    for root, _, files in os.walk("."):
        if is_ignored(Path(root), ignore_patterns):
            continue
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix == ".py" and not is_ignored(file_path, ignore_patterns):
                python_files.append(file_path)
    return python_files


def load_last_selection():
    """Loads the last file selection from a pickle file."""
    if Path(PICKLE_FILE).exists():
        with open(PICKLE_FILE, "rb") as f:
            return pickle.load(f)
    return set()


def save_last_selection(selected_files):
    """Saves the last file selection to a pickle file."""
    with open(PICKLE_FILE, "wb") as f:
        pickle.dump(selected_files, f)


def collect_file_data(selected_files):
    """Collects data from the specified files and returns a dictionary with titles and contents, with titles as comments."""
    file_data = {}

    for file_path in selected_files:
        if os.path.isfile(file_path):  # Ensure the file path is valid
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_title = os.path.basename(file_path)  # Extract the file name
                    file_contents = f.read()  # Read file contents as plain text
                    # Add file name as a comment at the start of the contents
                    # Ensure the file name is only included as a comment
                    file_data[file_title] = file_contents.strip()
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")

    return file_data


def copy_to_clipboard(text):
    """Copies text to the clipboard as plaintext."""
    if isinstance(text, str):
        pyperclip.copy(text)
    else:
        pyperclip.copy(str(text))
