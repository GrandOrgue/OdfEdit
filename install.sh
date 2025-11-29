#!/bin/bash
# Robustly set up ODFEdit virtual environment
# Assumes Python 3.10 framework build is installed

set -e

# ---------------------------
# Configuration
# ---------------------------
PYTHON_BIN=python3
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# ---------------------------
# Step 1: Remove old venv
# ---------------------------
if [ -d "$VENV_DIR" ]; then
    echo "Removing old virtual environment..."
    rm -rf "$VENV_DIR"
fi

# ---------------------------
# Step 2: Create new venv
# ---------------------------
echo "Creating virtual environment..."
$PYTHON_BIN -m venv "$VENV_DIR" --system-site-packages

# ---------------------------
# Step 3: Activate venv
# ---------------------------
source "$VENV_DIR/bin/activate"

# ---------------------------
# Step 4: Install ODFEdit dependencies
# ---------------------------
echo "Installing ODFEdit dependencies..."
if ! python3 -c "from PIL import ImageTk" 2>/dev/null; then
    echo "Pillow missing or ImageTk unavailable, installing from source..."
    pip install --force-reinstall --no-binary :all: pillow
else
    echo "Pillow with ImageTk is already installed."
fi
pip install .

echo "ODFEdit setup complete!"
echo "Run with: ./odfedit.sh"
