#!/bin/bash
# Run script for ChatGPT-Feeder (Linux/macOS)
# Automatically sets up environment if needed, then runs the application

set -e

echo "=== ChatGPT-Feeder ==="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.7 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "Found Python: $PYTHON_VERSION"

# Virtual environment path
VENV_PATH=".venv"
VENV_PYTHON="$VENV_PATH/bin/python"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Virtual environment not found. Running setup..."
    echo ""
    ./setup.sh
    echo ""
fi

# Check if dependencies are installed
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Virtual environment appears incomplete. Running setup..."
    echo ""
    ./setup.sh
    echo ""
fi

# Check if virtual environment is already activated
if [ -z "$VIRTUAL_ENV" ] || [ "$VIRTUAL_ENV" != "$(pwd)/$VENV_PATH" ]; then
    # Activate virtual environment
    echo "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
else
    echo "Virtual environment already active"
fi

# Verify dependencies are installed
echo "Verifying dependencies..."
python -c "import PySide6; import pyperclip" 2>&1 > /dev/null || {
    echo "Dependencies missing. Installing..."
    pip install -r requirements.txt --quiet
}

# Run the application
echo "Starting application..."
echo ""
python main.py

