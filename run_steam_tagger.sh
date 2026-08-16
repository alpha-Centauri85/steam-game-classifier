#!/usr/bin/env bash
# Linux launcher for the Steam Classifier command-line tool.
# Mirrors run_steam_tagger.bat. Uses a project-local virtual environment so
# nothing is installed system-wide (required on immutable distros such as
# Bazzite/Silverblue).
set -uo pipefail

cd "$(dirname "$(readlink -f "$0")")"

VENV=".venv"
PY="$VENV/bin/python"

echo
echo "============================================================"
echo "  Steam Collection Auto-Tagger"
echo "============================================================"
echo
echo "Before you start:"
echo "  1. Close Steam completely"
echo "  2. Get a free API key from: https://steamcommunity.com/dev/apikey"
echo "     (Use any domain name, e.g. localhost)"
echo "  3. Find your 64-bit Steam ID at: https://www.steamidfinder.com/"
echo "     (It's a 17-digit number starting with 76561)"
echo
echo "============================================================"
echo

if [ ! -x "$PY" ]; then
    echo "First run: creating virtual environment in $VENV ..."
    python3 -m venv "$VENV" || exit 1
    "$PY" -m pip install -r requirements.txt --quiet --disable-pip-version-check || exit 1
    echo
fi

read -r -p "Paste your Steam API key: " API_KEY
if [ -z "$API_KEY" ]; then
    echo "No API key entered. Exiting."
    exit 1
fi

read -r -p "Paste your 64-bit Steam ID: " STEAM_ID
if [ -z "$STEAM_ID" ]; then
    echo "No Steam ID entered. Exiting."
    exit 1
fi

echo
echo "Running preview (no changes will be made)..."
echo "Note: new/unrecognized games won't be asked about yet during preview."
echo "============================================================"
echo

"$PY" steam_categorizer_v2.py --api-key "$API_KEY" --steam-id "$STEAM_ID" --dry-run --overwrite

echo
echo "============================================================"
echo
read -r -p "Look good? Type YES to apply changes, anything else to cancel: " CONFIRM

if [ "${CONFIRM^^}" = "YES" ]; then
    echo
    echo "Applying categories..."
    echo "If any new games are found, you'll be asked to confirm a category"
    echo "for each one right here - just follow the prompts."
    echo
    "$PY" steam_categorizer_v2.py --api-key "$API_KEY" --steam-id "$STEAM_ID" --overwrite
    echo
    echo "Done! You can now open Steam."
else
    echo
    echo "Cancelled. No changes were made."
fi
echo
