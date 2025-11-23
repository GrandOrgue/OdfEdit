#!/bin/bash
# Activate venv and run ODFEdit
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/venv/bin/activate"
exec python "$DIR/src/OdfEdit.py" "$@"
