#!/bin/bash
# Setup script for ChatGPT-Feeder (Linux/macOS)
# Creates virtual environment and installs dependencies

set -e

echo "=== ChatGPT-Feeder Setup ==="
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

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
    echo "Virtual environment created successfully"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip --quiet || echo "Warning: Failed to upgrade pip, continuing anyway..."

# Install runtime dependencies
echo "Installing runtime dependencies..."
pip install -r requirements.txt

echo ""
echo "=== Setup Complete! ==="
echo "You can now run the application with: ./run.sh"
echo "Or manually: source .venv/bin/activate then python main.py"





