import shutil
import subprocess
import sys

from venv_utils import (
    check_pip_available,
    check_python_available,
    create_venv,
    ensure_pip_installed,
    get_requirements_file,
    install_dependencies,
)

# --- Configuration ---
VENV_DIR = ".venv"


def main():
    print("⚙️  Starting Setup for Spoon (Pazal Group SRL)...")

    # 1. Check Python availability
    if not check_python_available():
        print("❌ Error: Python is not installed or not in PATH")
        print("Please install Python 3.7 or higher from https://www.python.org/")
        sys.exit(1)

    # 2. Create Virtual Environment if it doesn't exist
    venv_python = create_venv(VENV_DIR)

    # 3. Ensure pip is installed in the venv
    if not ensure_pip_installed(venv_python):
        print("⚠️  Warning: pip is not available. Some operations may fail.")

    # 4. Upgrade pip (only if pip is available and uv is not being used)
    # If uv is available, it manages pip, so we skip this step
    uv_path = shutil.which("uv")
    if not uv_path and check_pip_available(venv_python):
        # Only upgrade pip if we're not using uv and pip is available
        try:
            subprocess.run(
                [
                    venv_python,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "pip",
                    "--quiet",
                    "--disable-pip-version-check",
                ],
                check=True,
            )
        except subprocess.CalledProcessError:
            print("⚠️  Warning: Failed to upgrade pip.")

    # 5. Install Dependencies
    # Use requirements.txt (not requirements-dev.txt) for setup
    requirements_file = get_requirements_file(prioritize_dev=False)
    if requirements_file:
        install_dependencies(venv_python, requirements_file, quiet=True)

    print("✅ Setup complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Setup cancelled.")
        sys.exit(1)
