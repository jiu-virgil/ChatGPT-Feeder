"""
Curated Icon Downloader for Spoon.

Downloads only essential language and folder icons, avoiding bloat.
"""

import sys
import os
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Run: pip install requests")
    sys.exit(1)

# --- CONFIGURATION ---
REPO_BASE = "https://raw.githubusercontent.com/vscode-icons/vscode-icons/master/icons"
LOCAL_ICONS_DIR = Path("resources/icons")
MANIFEST_PATH = Path("src/utils/icon_manifest.py")

# 1. The Core System Icons (Must Have)
SYSTEM_ICONS = [
    "default_file.svg",
    "default_folder.svg",
    "default_folder_opened.svg",
    "chevron-right.svg",  # For collapsed tree branches
    "chevron-down.svg",   # For expanded tree branches
]

# 2. Common Folder Names (e.g. "src", "test")
# Format: "folder_type_{name}.svg" and "folder_type_{name}_opened.svg"
FOLDER_NAMES = [
    "src", "dist", "out", "build", "target",
    "test", "tests", "__tests__", "spec",
    "docs", "documentation",
    "assets", "images", "icons", "resources",
    "components", "views", "controllers", "services", "utils", "lib",
    "api", "routes", "router",
    "config", "settings",
    "scripts", "tools",
    "node_modules", "venv", ".venv", "env",
    ".git", ".github", ".vscode", ".idea",
    "public", "static",
    "include", "inc",
    "db", "database", "sql",
    "log", "logs",
    "temp", "tmp",
]

# 3. File Types (Languages & Tools)
# Format: "file_type_{name}.svg"
FILE_TYPES = [
    # Languages
    "python", "python2", "python3",
    "js", "javascript", "js_official",
    "ts", "typescript", "typescript_official",
    "html", "htm",
    "css", "scss", "sass", "less",
    "json", "json_official", "json2", "json5",
    "xml", "yaml", "yml",
    "markdown", "md",
    "php", "php2", "php3",
    "c", "cpp", "csharp", "csharp2",
    "java", "class", "jar",
    "go", "gopher",
    "rust", "cargo",
    "ruby", "gemfile",
    "swift",
    "lua",
    "perl",
    "r",
    "shell", "bat", "powershell",
    "sql", "sqlite", "mysql", "pgsql",
    
    # Frameworks / Configs
    "reactjs", "reactts",
    "vue", "vueconfig",
    "angular",
    "docker", "dockerfile",
    "git", "gitignore",
    "npm", "yarn", "pnpm",
    "webpack", "rollup", "vite", "babel",
    "eslint", "prettier",
    "env", "dotenv",
    "license",
    "text", "log",
    "zip", "pdf", "image", "svg",
    "exe", "dll",
]

def build_download_list() -> list[str]:
    """Construct the full list of filenames to download."""
    targets = set(SYSTEM_ICONS)
    
    # Add folders (closed and opened)
    for name in FOLDER_NAMES:
        targets.add(f"folder_type_{name}.svg")
        targets.add(f"folder_type_{name}_opened.svg")
        
    # Add files
    for name in FILE_TYPES:
        targets.add(f"file_type_{name}.svg")
        
    return sorted(list(targets))

def download_file(filename: str) -> tuple[str, bool]:
    """Download a single file. Returns (filename, success)."""
    url = f"{REPO_BASE}/{filename}"
    local_path = LOCAL_ICONS_DIR / filename
    
    # Optional: Skip if exists (uncomment to cache)
    # if local_path.exists(): return filename, True

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            local_path.write_bytes(response.content)
            return filename, True
        return filename, False
    except Exception:
        return filename, False

def generate_manifest(files: list[str]) -> None:
    """Generate the static python manifest."""
    print(f"\nGenerating manifest at {MANIFEST_PATH}...")
    
    # Only include files that actually exist on disk
    valid_files = [f for f in files if (LOCAL_ICONS_DIR / f).exists()]
    
    # Also scan for any additional SVG files in the directory
    if LOCAL_ICONS_DIR.exists():
        try:
            for entry in os.scandir(LOCAL_ICONS_DIR):
                if entry.is_file() and entry.name.endswith(".svg"):
                    if entry.name not in valid_files:
                        valid_files.append(entry.name)
        except Exception as e:
            print(f"Warning: Could not scan icons directory: {e}")
    
    if not valid_files:
        print("Warning: No valid icon files found. Manifest will be empty.")
    
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        f.write('"""Auto-generated icon manifest. Do not edit manually."""\n\n')
        if valid_files:
            f.write("AVAILABLE_ICONS = {\n")
        for name in sorted(valid_files):
            f.write(f'    "{name}",\n')
        f.write("}\n")
        else:
            f.write("# No icons found. Run download_icons.py to download icons.\n")
            f.write("AVAILABLE_ICONS = None\n")
    
    print(f"  Generated manifest with {len(valid_files)} icon(s)")

def main():
    print("="*50)
    print("  Curated VS Code Icons Downloader")
    print("="*50)
    
    # Setup
    LOCAL_ICONS_DIR.mkdir(parents=True, exist_ok=True)
    targets = build_download_list()
    
    print(f"Targeting {len(targets)} essential icons...")
    
    success_count = 0
    failed_count = 0
    
    # Parallel Download
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(download_file, name): name for name in targets}
        
        for i, future in enumerate(as_completed(futures)):
            name, success = future.result()
            if success:
                success_count += 1
                # print(f"[{i+1}/{len(targets)}] Downloaded {name}")
            else:
                failed_count += 1
                # Some will fail (e.g. folder variants that don't exist), this is expected.
                # print(f"[{i+1}/{len(targets)}] Skipped/Missing {name}")

    print(f"\nSummary:")
    print(f"  Downloaded: {success_count}")
    print(f"  Missing/Skipped: {failed_count} (Normal for some folder variants)")
    
    # Generate Manifest
    generate_manifest(targets)
    print("\nDone! Please rebuild your app.")

if __name__ == "__main__":
    main()
