import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime

from venv_utils import (
    check_python_available,
    create_venv,
    get_requirements_file,
    get_venv_python_path,
    install_dependencies,
)

# --- Configuration ---
COMPANY_NAME = "Pazal Group SRL"
PRODUCT_NAME = "Spoon"
FILE_VERSION = "1.0.0.0"
PRODUCT_VERSION = "1.0.0.0"
COPYRIGHT = f"Copyright (C) {datetime.now().year} {COMPANY_NAME}"
OUTPUT_FILENAME = "Spoon.exe"
DIST_DIR = "dist"
ICON_PATH = os.path.join("resources", "spoon.ico")


def setup_environment(venv_dir=".venv", skip_deps=False):
    """
    Sets up the virtual environment and installs dependencies.
    Prioritizes 'requirements-dev.txt' over 'requirements.txt'.
    """
    if skip_deps:
        print("⏭️  Skipping dependency checks as requested.")
        return get_venv_python_path(venv_dir)

    # 1. Create Virtual Environment if missing
    venv_python = create_venv(venv_dir)

    # 2. Determine Requirements File (prioritize dev for build)
    req_file = get_requirements_file(prioritize_dev=True)

    if req_file:
        install_dependencies(venv_python, req_file, quiet=False)

    return venv_python


def check_cpp_compiler():
    """Checks for C++ compiler (MSVC or MinGW) and returns compiler type."""
    if platform.system() != "Windows":
        return False, None

    # Check for MSVC (cl.exe)
    msvc_path = shutil.which("cl")
    if msvc_path:
        try:
            # Verify it actually works by checking version
            result = subprocess.run(
                [msvc_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                capture_output=True,
            )
            # cl.exe returns non-zero exit code when called without args, but that's OK
            return True, "MSVC"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Check for MinGW (gcc)
    gcc_path = shutil.which("gcc")
    if gcc_path:
        try:
            result = subprocess.run(
                [gcc_path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                capture_output=True,
            )
            if result.returncode == 0:
                return True, "MinGW"
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass

    return False, None


def remove_existing_executable(backend="nuitka"):
    """Removes existing executable to avoid permission errors."""
    exe_name = OUTPUT_FILENAME if backend == "nuitka" else f"{PRODUCT_NAME}.exe"
    exe_path = os.path.join(DIST_DIR, exe_name)

    if os.path.exists(exe_path):
        print("🗑️  Removing existing executable...")
        try:
            os.remove(exe_path)
            print(f"   - Removed {exe_name}")
        except PermissionError:
            print(
                "   ⚠️  Warning: Could not remove existing executable (it may be running)"
            )
            print(f"   Please close any running instances of {exe_name} and try again")
            sys.exit(1)
        except Exception as e:
            print(f"   ⚠️  Could not remove {exe_name}: {e}")


def clean_build():
    """Removes build artifacts."""
    print("🧹 Cleaning build directories...")
    dirs_to_remove = [DIST_DIR, "build", "Spoon.build", "__pycache__"]
    for d in dirs_to_remove:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
                print(f"   - Removed {d}")
            except Exception as e:
                print(f"   ⚠️ Could not remove {d}: {e}")


def sign_executable(target_path):
    """Calls the external PowerShell script to sign the executable."""
    script_name = "sign_executable.ps1"
    if not os.path.exists(script_name):
        print(f"⚠️  Signing skipped: '{script_name}' not found.")
        print("   (To enable signing, ensure the script and certificate are present)")
        return

    print(f"🔐 Signing executable using {script_name}...")
    try:
        # We use powershell to run the signing script
        subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                script_name,
                target_path,
            ],
            check=True,
        )
        print("✅ Signing complete.")
    except subprocess.CalledProcessError:
        print("❌ Signing failed.")


def prepare_ms_store():
    """Prepares the folder structure for Microsoft Store (MSIX) packaging."""
    print("🏪 Preparing Microsoft Store build layout...")

    store_dir = "ms-store-layout"
    if not os.path.exists(store_dir):
        os.makedirs(store_dir)
        print(f"   - Created '{store_dir}' directory")

    # Check for critical assets
    missing = []
    if not os.path.exists("AppxManifest.xml"):
        missing.append("AppxManifest.xml")

    assets_dir = os.path.join("resources", "Assets")
    if not os.path.exists(assets_dir):
        missing.append("resources/Assets folder")

    if missing:
        print("⚠️  Warning: The following MS Store files are missing:")
        for m in missing:
            print(f"   - {m}")
    else:
        print("✅ MS Store assets appear to be present.")
        # Logic to copy files to store_dir could go here if needed
        # shutil.copy("AppxManifest.xml", store_dir)


def run_nuitka_build(python_path, target_file, fast=False, show_progress=False):
    build_mode = "fast" if fast else "optimized"
    print(f"🚀 Starting Nuitka build for '{target_file}' ({build_mode} mode)...")

    cmd = [
        python_path,
        "-m",
        "nuitka",
        "--standalone",
        "--windows-disable-console",
        "--onefile",
        f"--output-filename={OUTPUT_FILENAME}",
        f"--output-dir={DIST_DIR}",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--python-flag=-O",  # Python Optimize flag
        "--no-pyi-file",  # Don't generate pyi file
        # Plugins
        "--enable-plugin=pyside6",
        # Resources & Data
        f"--windows-icon-from-ico={ICON_PATH}",
        "--include-data-dir=resources=resources",
        "--include-data-dir=src=src",
        # Company Metadata
        f"--company-name={COMPANY_NAME}",
        f"--product-name={PRODUCT_NAME}",
        f"--file-version={FILE_VERSION}",
        f"--product-version={PRODUCT_VERSION}",
        f"--copyright={COPYRIGHT}",
    ]

    # Add LTO only for optimized (non-fast) builds
    if not fast:
        cmd.append("--lto=yes")  # Link Time Optimization
    else:
        print("   ⚡ Fast mode: LTO disabled for faster builds")

    cmd.append(target_file)

    # Set up environment with cache directory for incremental builds
    env = os.environ.copy()
    cache_dir = os.path.abspath(".nuitka-cache")
    env["NUITKA_CACHE_DIR"] = cache_dir

    if show_progress:
        print("   [Progress] Building (showing output)...")
        print(f"   📦 Cache directory: {cache_dir}")
        try:
            subprocess.run(cmd, check=True, env=env)
            print("\r   [Progress] Build completed successfully")
        except subprocess.CalledProcessError as e:
            print("\r   [Progress] Build failed")
            print(f"\n❌ Build failed with error code {e.returncode}.")
            sys.exit(1)
    else:
        print("   [Progress] Building...", end="", flush=True)
        try:
            result = subprocess.run(
                cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env
            )
            print("\r   [Progress] Build completed successfully")
        except subprocess.CalledProcessError as e:
            print("\r   [Progress] Build failed")
            print(f"\n❌ Build failed with error code {e.returncode}.")
            # Show error output
            error_output = ""
            stderr_output = ""
            stdout_output = ""
            if e.stderr:
                stderr_output = e.stderr.decode("utf-8", errors="replace")
                error_output = stderr_output
            if e.stdout:
                stdout_output = e.stdout.decode("utf-8", errors="replace")
                if not error_output:
                    error_output = stdout_output

            if error_output:
                print("\nError output:")
                # Show last 50 lines to avoid overwhelming output
                lines = error_output.strip().split("\n")
                if len(lines) > 50:
                    print("... (showing last 50 lines) ...")
                    print("\n".join(lines[-50:]))
                else:
                    print(error_output)
            else:
                print(
                    "\n⚠️  No error output captured. This might indicate a subprocess issue."
                )
            print("\n💡 Tip: Use --show-progress to see full build output")
            sys.exit(1)


def run_pyinstaller_build(python_path, target_file, clean=False):
    print(f"📦 Starting PyInstaller build for '{target_file}'...")

    # Check if main.spec exists - use it if available
    if os.path.exists("main.spec"):
        print("   Using main.spec file...")
        cmd = [
            python_path,
            "-m",
            "PyInstaller",
            "main.spec",
            "--noconfirm",
            "--log-level=WARN",
        ]
        if clean:
            cmd.append("--clean")
    else:
        # Fall back to command-line approach
        print("   Using command-line configuration...")
        cmd = [
            python_path,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--onefile",
            "--windowed",
            f"--name={PRODUCT_NAME}",
            f"--icon={ICON_PATH}",
            "--add-data=resources;resources",
            "--add-data=src;src",
            "--distpath",
            DIST_DIR,
            target_file,
        ]

    print("   [Progress] Building...", end="", flush=True)
    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print("\r   [Progress] Build completed successfully")
    except subprocess.CalledProcessError as e:
        print("\r   [Progress] Build failed")
        print(f"\n❌ Build failed with error code {e.returncode}.")
        print("Re-run the build to see error messages, or check PyInstaller logs.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description=f"{PRODUCT_NAME} Build Tool - {COMPANY_NAME}"
    )

    parser.add_argument(
        "--backend",
        type=str,
        default="nuitka",
        choices=["nuitka", "pyinstaller", "run"],
        help="Build backend (default: nuitka)",
    )
    parser.add_argument(
        "--target", type=str, default="main.py", help="Entry point (default: main.py)"
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean build directories before starting"
    )
    parser.add_argument(
        "--skip-deps", action="store_true", help="Skip dependency installation"
    )
    parser.add_argument(
        "--ms-store", action="store_true", help="Prepare for Microsoft Store"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast build mode: disable LTO and other expensive optimizations for faster development builds",
    )
    parser.add_argument(
        "--no-sign",
        action="store_true",
        help="Skip code signing (faster for development builds)",
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Show build progress output instead of suppressing it",
    )

    args = parser.parse_args()

    start_time = time.time()

    # Check Python availability
    if not check_python_available():
        print("❌ Error: Python is not installed or not in PATH")
        print("Please install Python 3.7 or higher from https://www.python.org/")
        sys.exit(1)

    if args.clean:
        clean_build()

    if not os.path.exists(args.target):
        print(f"Error: Target file '{args.target}' does not exist.")
        sys.exit(1)

    # Setup Env
    venv_python = setup_environment(skip_deps=args.skip_deps)

    # Remove existing executable before build (if not cleaning)
    if not args.clean and args.backend != "run":
        remove_existing_executable(args.backend)

    # Run Build/Execute
    if args.backend == "run":
        print(f"🐍 Running '{args.target}'...")
        subprocess.run([venv_python, args.target])
        return

    elif args.backend == "nuitka":
        # Check for C++ compiler
        compiler_found, compiler_type = check_cpp_compiler()
        if compiler_found:
            print(f"🔧 Found C++ compiler: {compiler_type}")
        else:
            print("⚠️  No C++ compiler detected. Nuitka will auto-download MinGW...")
        print()
        run_nuitka_build(
            venv_python, args.target, fast=args.fast, show_progress=args.show_progress
        )

    elif args.backend == "pyinstaller":
        run_pyinstaller_build(venv_python, args.target, clean=args.clean)

    # Post-Build Steps
    exe_path = os.path.join(
        DIST_DIR, OUTPUT_FILENAME if args.backend == "nuitka" else f"{PRODUCT_NAME}.exe"
    )

    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n✅ Build verified: {exe_path}")
        print(f"   Size: {size_mb:.2f} MB")

        # Code Signing
        if not args.no_sign:
            sign_executable(exe_path)
        else:
            print("⏭️  Code signing skipped (--no-sign flag)")

        # MS Store Prep
        if args.ms_store:
            prepare_ms_store()

        print(
            "\n💡 Tip: Run 'refresh_icon_cache.ps1' if the icon doesn't update in Explorer."
        )
    else:
        print(f"\n❌ Build verification failed: Executable not found at {exe_path}")

    duration = time.time() - start_time
    if duration >= 60:
        minutes = duration / 60
        print(f"⏱️  Total time: {duration:.1f} seconds ({minutes:.1f} minutes)")
    else:
        print(f"⏱️  Total time: {duration:.1f} seconds")


if __name__ == "__main__":
    main()
