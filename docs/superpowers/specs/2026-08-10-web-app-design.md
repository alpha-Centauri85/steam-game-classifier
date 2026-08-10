# Steam Game Classifier — Web App Design

**Date:** 2026-08-10
**Status:** Approved (pending spec review)

## Goal

Turn the existing command-line Steam categoriser into a self-contained local
web app with a friendly front end, so it can be handed to a non-technical
person who runs it on their own PC. The current CLI must keep working
unchanged.

## Key decisions

- **Runs on the user's own PC.** The backend must reach the user's local Steam
  files (`cloud-storage-namespace-1.json`), so it runs locally, not hosted.
- **v1 is a guided 4-step wizard** that mirrors the current CLI flow. Room to
  grow into a full "library manager" later without changing the backend.
- **Credentials are remembered locally** (gitignored `config.json`), with a
  "forget" option in the UI.
- **Stack: Python + plain web UI (no build step).** Flask backend serving a
  hand-written HTML/CSS/JS page. One process, one language, no Node toolchain.
  Chosen for ease of handover and maintenance over a React build.

## Architecture

One Flask process serves a static page and a small JSON API, and opens the
browser automatically on launch.

Core logic is extracted out of `steam_categorizer_v2.py` (which today mixes
core logic, CLI arg parsing, and interactive terminal prompts) into an
importable `steam_core.py`. Both the CLI and the web app import the same core,
so there is exactly one copy of the real work.

```
steam-game-classifier/
  steam_core.py            # NEW: shared logic (find file, fetch games, categorise, backup, write)
  steam_categorizer_v2.py  # KEPT: CLI, refactored to import steam_core (behaviour unchanged for users)
  app.py                   # NEW: Flask app + routes + browser launch
  static/
    index.html             # the wizard
    style.css              # modern styling, light + dark
    app.js                 # wizard logic, talks to the API
  requirements.txt         # flask, requests
  run_web.bat              # NEW: double-click launcher for the web app
  run_steam_tagger.bat     # KEPT: existing CLI launcher
  tests/                   # pytest tests for steam_core
  README.md
```

## Components (units and responsibilities)

- **steam_core.py** — pure-ish logic, no terminal I/O. Responsibilities:
  find the Steam cloud JSON, fetch owned games from the Steam Web API,
  categorise a game (built-in map + learned categories), load/save learned
  categories, back up the cloud JSON, write category assignments back.
  Exposes functions the CLI and web layer both call. No `input()`, no
  `print()` used for control flow (return values / raise exceptions instead).
- **steam_categorizer_v2.py** — CLI entry point. Owns argparse and the
  interactive terminal prompts; delegates all real work to `steam_core`.
- **app.py** — Flask app. Owns HTTP routes, request/response shaping,
  reading/writing `config.json`, and launching the browser. Delegates all
  real work to `steam_core`.
- **static/** — the wizard UI. `app.js` calls the API and renders state; no
  business logic lives here beyond presentation.

## Wizard flow

1. **Setup** — Enter/confirm API key + Steam ID (pre-filled if remembered).
   Saved to gitignored `config.json`; a "forget" link clears it. Backend
   checks whether Steam is running and warns (the file must be edited with
   Steam closed).
2. **Preview (dry run)** — Backend fetches owned games and categorises them.
   **Nothing is written to disk.** Returns a before→after view grouped into:
   - **Will change** — game, current category → proposed category (highlighted).
   - **Needs your input** — unknown games (resolved in step 3).
   - **No change** — already correct, or deliberately left alone.
   A checkbox controls "re-categorise games that already have a category"
   (off by default = current safe behaviour).
3. **Unknowns** — Each unrecognised game gets a dropdown of valid categories.
   Choices are saved as learned categories so they auto-match next time.
4. **Apply** — Backend backs up the cloud JSON (timestamped, as today), writes
   the assignments, saves learned choices, and shows a summary.

**Preview/Apply guarantee:** Apply writes exactly what the preview showed,
nothing more. The end summary reflects the same list, so the change is
traceable from preview through to result.

## API (all local, localhost only)

- `GET  /api/config` — return saved config (API key masked in the response).
- `POST /api/config` — save API key + Steam ID (+ optional Steam path).
- `DELETE /api/config` — forget stored credentials.
- `GET  /api/steam-status` — is Steam running? is the cloud JSON found?
- `GET  /api/categories` — list of valid category names for dropdowns.
- `POST /api/preview` — body: key, id, overwrite flag. Returns the grouped
  before→after change set and the list of unknown games. Writes nothing.
- `POST /api/apply` — body: the final assignments (including resolved
  unknowns). Backs up, writes, saves learned categories, returns a summary.

## Error handling

Each of these returns a clear message the UI displays, instead of crashing:

- Steam cloud JSON not found (bad/nonexistent install path).
- Steam is currently running (warn before apply; block apply).
- Invalid API key or malformed/wrong Steam ID.
- Steam Web API unreachable / network error / non-200 response.
- Malformed existing `categories.json` (warn, continue with built-in map).
- Write failure mid-apply (report which file, backup already exists to restore).

The existing backup-before-write behaviour is kept and surfaced in the UI
(the summary names the backup file created).

## Testing

`steam_core.py` is unit-testable in isolation with pytest:

- Categorisation mapping: known game → expected category; case/whitespace
  handling; learned categories override/extend the built-in map.
- Learned categories load/save round-trip; malformed file handled gracefully.
- Owned-games parsing from a mocked Steam API response.
- Preview change-set grouping logic (will change / unknown / no change),
  including the overwrite flag on/off.

Tests mock the Steam Web API and file I/O so they never touch a real Steam
install or hit the network.

## Out of scope (v1)

- Hosted/multi-user version.
- Full library manager (search, bulk edit, drag-and-drop) — deferred to v2.
- Packaging into a standalone .exe — revisit after the app works.
- Authentication (it's a local single-user app on localhost).

## Non-goals / guarantees

- The CLI's user-facing behaviour does not change.
- No credentials or personal runtime files are committed to git
  (`config.json`, `categories.json`, backups stay gitignored).
