#!/usr/bin/env bash
# Linux launcher for the Steam Classifier web wizard.
# Mirrors run_web.bat. Uses a project-local virtual environment so nothing is
# installed system-wide (required on immutable distros such as Bazzite/Silverblue).
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

VENV=".venv"
PY="$VENV/bin/python"

echo "Starting Steam Classifier..."
echo "A browser tab will open at http://127.0.0.1:5000"
echo "Press Ctrl+C to stop the app."
echo

if [ ! -x "$PY" ]; then
    echo "First run: creating virtual environment in $VENV ..."
    python3 -m venv "$VENV"
fi

"$PY" -m pip install -r requirements.txt --quiet --disable-pip-version-check

exec "$PY" app.py
