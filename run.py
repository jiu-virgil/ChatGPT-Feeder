import os
import platform
import subprocess
import sys

from venv_utils import (
    check_dependencies,
    check_python_available,
    get_venv_python_path,
)

# --- Configuration ---
VENV_DIR = ".venv"
MAIN_SCRIPT = "main.py"
SETUP_SCRIPT = "setup.py"


def run_setup():
    """Executes the setup.py script."""
    if not os.path.exists(SETUP_SCRIPT):
        print(f"❌ Error: {SETUP_SCRIPT} not found.")
        sys.exit(1)

    print("🔄 Environment incomplete. Running setup...")
    try:
        subprocess.run([sys.executable, SETUP_SCRIPT], check=True)
    except subprocess.CalledProcessError:
        print("❌ Error: Setup failed. Please run setup.py manually.")
        sys.exit(1)


def main():
    # 1. Check Python availability
    if not check_python_available():
        print("❌ Error: Python is not installed or not in PATH")
        print("Please install Python 3.7 or higher from https://www.python.org/")
        sys.exit(1)

    # 2. Check if virtual environment exists
    venv_python = get_venv_python_path(VENV_DIR)

    if not os.path.exists(VENV_DIR) or not os.path.exists(venv_python):
        run_setup()

    # 3. Check dependencies
    # We check using the VENV python, not the system python
    if not check_dependencies(venv_python):
        print("⚠️  Dependencies missing or broken.")
        run_setup()
        # Re-check after setup
        if not check_dependencies(venv_python):
            print("❌ Error: Failed to install dependencies even after setup.")
            sys.exit(1)

    # 4. Run the application
    # We explicitly call the venv python to run main.py, which achieves
    # the same result as 'activating' the environment in shell.
    print(f"🚀 Launching {MAIN_SCRIPT}...")
    try:
        # Pass through any arguments given to this script
        args = [venv_python, MAIN_SCRIPT] + sys.argv[1:]

        # Replace the current process with the application to keep PID (Unix)
        # or just run it (Windows)
        if platform.system() == "Windows":
            subprocess.run(args, check=True)
        else:
            os.execv(venv_python, args)

    except subprocess.CalledProcessError as e:
        print(f"❌ Application exited with code {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()
