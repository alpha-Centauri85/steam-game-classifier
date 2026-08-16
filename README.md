# Steam Game Classifier

Automatically assigns collection categories to uncategorised games in your Steam
library. It reads your owned games via the Steam Web API, matches each one against
a built-in category map (and any categories you've taught it), and writes the
results back into Steam's local collections file.

New or unrecognised games can be categorised interactively, and your choices are
remembered for next time.

## Web app (recommended)

A guided, step-by-step wizard that runs in your browser.

### Requirements

- Python 3
- `pip install -r requirements.txt`

### Launch

**Windows** — double-click `run_web.bat`, or run `python app.py` from a terminal.

**Linux** — run `./run_web.sh` from a terminal. On first run it creates a
project-local virtual environment in `.venv/` and installs the dependencies
there, so nothing is written system-wide. This is what makes it work on
immutable distros such as Bazzite, Fedora Silverblue, and SteamOS, where the
system Python is read-only.

A browser tab opens automatically at http://127.0.0.1:5000. The wizard walks you
through connecting your Steam account, previewing changes, sorting any new games,
and applying the result.

> **Close and sign out of Steam on every device before applying.** Collections
> sync through Steam Cloud, so if Steam is still signed in on another PC,
> laptop, or Steam Deck, it can undo your changes on its next sync or hide
> them until that device signs out and back in. The wizard's final step asks
> you to confirm this before it lets you apply anything.

## Command-line version

The steps below describe the original command-line tool, which still works
if you prefer it to the web app.

## Requirements

- Python 3
- `pip install requests`

## Setup

1. Get a free Steam Web API key: https://steamcommunity.com/dev/apikey
   (use any domain, e.g. `localhost`).
2. Find your 64-bit Steam ID: https://www.steamidfinder.com/
   (a 17-digit number starting with `76561`).

> **Close Steam completely before running.** The script edits Steam's local
> collections file, and Steam will overwrite your changes if it's open.

## Usage

### Easy mode

**Windows** — double-click `run_steam_tagger.bat`.
**Linux** — run `./run_steam_tagger.sh`.

Either one prompts for your API key and Steam ID, runs a preview (dry run)
first, then asks before applying any changes. The Linux script bootstraps the
same `.venv/` virtual environment as the web launcher.

### Command line

```bash
# Preview only, no changes written
python steam_categorizer_v2.py --api-key YOUR_KEY --steam-id YOUR_64BIT_ID --dry-run

# Apply categories
python steam_categorizer_v2.py --api-key YOUR_KEY --steam-id YOUR_64BIT_ID

# Point at a non-default Steam install
python steam_categorizer_v2.py --api-key YOUR_KEY --steam-id YOUR_64BIT_ID --steam-path "D:/Steam"
```

## How it works

- Auto-detects your Steam install and locates
  `cloud-storage-namespace-1.json` under `userdata`. On Linux this resolves via
  `~/.steam/steam`, which native Steam symlinks to `~/.local/share/Steam`. If
  you run Steam as a Flatpak, pass `--steam-path
  ~/.var/app/com.valvesoftware.Steam/data/Steam` (or set the custom Steam path
  in the web wizard).
- Backs up that file (timestamped) before making any changes.
- Matches each game against the built-in `GAME_CATEGORIES` map.
- Prompts you to categorise anything it doesn't recognise, saving your answers
  to `categories.json` so they carry over to future runs.

## Notes

- `categories.json` (your learned categories) and the timestamped backups are
  local runtime files and are not tracked in git.
- Your API key and Steam ID are never stored in the code; they're passed in at
  runtime each time.
