"""
Shared utilities for virtual environment management.
Used by run.py, setup.py, and build.py to eliminate code duplication.
"""

import os
import platform
import shutil
import subprocess
import sys


def check_python_available():
    """Checks if Python is installed and in PATH."""
    try:
        subprocess.run(
            [sys.executable, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_venv_python_path(venv_dir=".venv"):
    """Returns the path to the python executable in the virtual environment."""
    if platform.system() == "Windows":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    return os.path.join(venv_dir, "bin", "python")


def create_venv(venv_dir=".venv"):
    """
    Creates virtual environment using uv (if available) or standard venv.
    Returns the path to the venv Python executable.
    Raises SystemExit on failure.
    """
    if os.path.exists(venv_dir):
        return get_venv_python_path(venv_dir)

    print(f"📦 Creating virtual environment in '{venv_dir}'...")
    uv_path = shutil.which("uv")
    created = False

    if uv_path:
        print("⚡ 'uv' detected. Creating venv with uv...")
        try:
            subprocess.run([uv_path, "venv", venv_dir, "--seed"], check=True)
            created = True
        except subprocess.CalledProcessError:
            print("⚠️ 'uv' venv creation failed. Falling back to standard venv...")

    if not created:
        try:
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        except subprocess.CalledProcessError:
            print("❌ Failed to create virtual environment.")
            sys.exit(1)

    venv_python = get_venv_python_path(venv_dir)
    if not os.path.exists(venv_python):
        print(f"❌ Error: Virtual environment python not found at {venv_python}")
        sys.exit(1)

    return venv_python


def get_requirements_file(prioritize_dev=True):
    """
    Returns the path to the requirements file.
    If prioritize_dev=True, prioritizes requirements-dev.txt over requirements.txt.
    Returns None if no requirements file is found.
    """
    if prioritize_dev and os.path.exists("requirements-dev.txt"):
        return "requirements-dev.txt"
    if os.path.exists("requirements.txt"):
        return "requirements.txt"
    return None


def prepare_venv_env(venv_dir, venv_python):
    """Prepares environment variables for uv/pip operations."""
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = os.path.abspath(venv_dir)
    env["PATH"] = os.path.dirname(venv_python) + os.pathsep + env.get("PATH", "")
    return env


def install_dependencies(venv_python, requirements_file, quiet=True):
    """
    Installs dependencies using uv (if available) or pip.
    Raises SystemExit on failure.
    """
    if not os.path.exists(requirements_file):
        print(f"ℹ️  {requirements_file} not found. Skipping dependency installation.")
        return

    print(f"📥 Installing dependencies from {requirements_file}...")

    venv_dir = os.path.dirname(os.path.dirname(venv_python))
    env = prepare_venv_env(venv_dir, venv_python)
    uv_path = shutil.which("uv")
    install_success = False

    if uv_path:
        print("⚡ 'uv' detected. Installing with high speed...")
        try:
            subprocess.run(
                [uv_path, "pip", "install", "-r", requirements_file],
                env=env,
                check=True,
            )
            install_success = True
        except subprocess.CalledProcessError:
            print("⚠️ 'uv' failed. Falling back to standard pip...")

    if not install_success:
        print("🐍 Installing with standard pip...")
        pip_args = [
            venv_python,
            "-m",
            "pip",
            "install",
            "-r",
            requirements_file,
        ]
        if quiet:
            pip_args.extend(["--quiet", "--disable-pip-version-check"])
        try:
            subprocess.run(pip_args, check=True)
        except subprocess.CalledProcessError:
            print("❌ Dependency installation failed.")
            sys.exit(1)


def check_pip_available(venv_python):
    """Checks if pip is available in the virtual environment."""
    try:
        subprocess.run(
            [venv_python, "-m", "pip", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def ensure_pip_installed(venv_python):
    """
    Ensures pip is installed in the virtual environment.
    Uses system pip or uv to bootstrap pip if it's missing.
    """
    if check_pip_available(venv_python):
        return True

    print("📦 Installing pip in virtual environment...")
    uv_path = shutil.which("uv")
    install_success = False

    # Try using uv first if available
    if uv_path:
        try:
            venv_dir = os.path.dirname(os.path.dirname(venv_python))
            env = prepare_venv_env(venv_dir, venv_python)
            subprocess.run(
                [uv_path, "pip", "install", "pip"],
                env=env,
                check=True,
            )
            install_success = True
        except subprocess.CalledProcessError:
            pass

    # Fallback: use ensurepip module (built into Python)
    if not install_success:
        try:
            subprocess.run(
                [venv_python, "-m", "ensurepip", "--upgrade"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            install_success = True
        except subprocess.CalledProcessError:
            pass

    # Last resort: use system pip with proper venv targeting
    if not install_success:
        system_pip = shutil.which("pip")
        if system_pip:
            try:
                venv_dir = os.path.dirname(os.path.dirname(venv_python))
                # Use system pip to install pip into the venv using --prefix
                subprocess.run(
                    [system_pip, "install", "--prefix", venv_dir, "pip"],
                    check=True,
                )
                install_success = True
            except subprocess.CalledProcessError:
                pass

    if not install_success:
        print("⚠️  Warning: Failed to install pip in virtual environment.")
        return False

    # Verify pip is now available
    if check_pip_available(venv_python):
        return True
    else:
        print("⚠️  Warning: pip installation completed but pip is still not available.")
        return False


def check_dependencies(venv_python, packages=None):
    """
    Checks if specific packages are importable.
    Default packages: ['PySide6', 'pyperclip']
    Returns True if all packages are importable, False otherwise.
    """
    if packages is None:
        packages = ["PySide6", "pyperclip"]

    import_cmd = "; ".join(f"import {pkg}" for pkg in packages)
    try:
        subprocess.run(
            [venv_python, "-c", import_cmd],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError:
        return False
