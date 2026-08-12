#!/usr/bin/env python3
"""
Steam Collection Auto-Tagger v2
Automatically assigns categories to uncategorized games in your Steam library.

Requirements:
    pip install requests

Setup:
    1. Get a free Steam API key: https://steamcommunity.com/dev/apikey
       (Use any domain, e.g. "localhost")
    2. Find your 64-bit Steam ID: https://www.steamidfinder.com/
       (17-digit number starting with 76561)

Usage:
    python steam_categorizer_v2.py --api-key YOUR_KEY --steam-id YOUR_64BIT_ID
    python steam_categorizer_v2.py --api-key YOUR_KEY --steam-id YOUR_64BIT_ID --dry-run
    python steam_categorizer_v2.py --api-key YOUR_KEY --steam-id YOUR_64BIT_ID --steam-path "D:/Steam"

IMPORTANT: Close Steam before running.

IMPORTANT: Close Steam before running.
"""

import sys
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime

import steam_core as core


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Steam Collection Auto-Tagger v2")
    parser.add_argument("--api-key",    required=True, help="Steam Web API key (https://steamcommunity.com/dev/apikey)")
    parser.add_argument("--steam-id",   required=True, help="Your 64-bit Steam ID (find at steamidfinder.com)")
    parser.add_argument("--steam-path", help="Custom Steam install path, e.g. D:/Steam")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--overwrite",  action="store_true",
                        help="Re-categorize games already in a collection")
    parser.add_argument("--no-prompt",  action="store_true",
                        help="Don't ask interactively about unmatched games")
    args = parser.parse_args()

    print()
    print("═" * 62)
    print("  Steam Collection Auto-Tagger v2")
    print("═" * 62)

    custom_categories = core.load_learned(core.CATEGORIES_FILE_DEFAULT)
    if custom_categories:
        print(f"Loaded {len(custom_categories)} learned categories from categories.json")

    try:
        CLOUD_JSON = core.find_cloud_json(args.steam_path)
    except core.AmbiguousAccountError as e:
        accounts = e.args[0]
        print("Multiple Steam accounts found:")
        for i, acc in enumerate(accounts):
            print(f"  {i+1}. Steam ID {acc}")
        idx = int(input("Select account number: ")) - 1
        chosen = accounts[idx]
        CLOUD_JSON = core.find_cloud_json(args.steam_path, account_id3=chosen)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)

    print(f"Steam user:  {CLOUD_JSON.parent.parent.parent.name}")
    print(f"Cloud file:  {CLOUD_JSON}")

    if not args.dry_run:
        backup_path = core.backup(CLOUD_JSON)
        print(f"✓ Backup: {backup_path.name}")
    else:
        print("  [DRY RUN — nothing will be written]")

    # Load JSON
    data = json.load(open(CLOUD_JSON, encoding="utf-8"))
    collections, already_categorized, max_version = core.load_collections(data)

    print(f"\nExisting collections: {len(collections)}")
    for name, info in sorted(collections.items()):
        print(f"  {name}: {len(info['added'])} games")

    # Fetch owned games
    print(f"\nFetching owned games from Steam API...")
    session = requests.Session()
    owned = core.get_owned_games(args.api_key, args.steam_id)
    print(f"Owned games: {len(owned)}")

    # Find uncategorized
    if args.overwrite:
        to_process = owned
    else:
        to_process = {aid: name for aid, name in owned.items()
                      if aid not in already_categorized}

    print(f"Games to categorize: {len(to_process)}")
    print()

    # Build collection_display_name → collection_name lookup
    # (maps our internal category keys to Steam collection display names)
    # Then map Steam display names to collection entries
    coll_by_display = {v: k for k, v in core.CATEGORY_TO_COLLECTION.items()}

    # Track changes: category_key → list of app IDs to add
    to_add       = {cat: [] for cat in core.CATEGORY_TO_COLLECTION}
    unmatched    = []
    soundtracks  = []

    for app_id, name in sorted(to_process.items(), key=lambda x: x[1]):
        category = core.categorize(name, custom_categories)
        if category == "SOUNDTRACKS":
            soundtracks.append((app_id, name))
            to_add["SOUNDTRACKS"].append(app_id)
        elif category:
            to_add[category].append(app_id)
            print(f"  ✓ {name}  →  {core.CATEGORY_TO_COLLECTION.get(category, category)}")
        else:
            unmatched.append((app_id, name))

    # Interactive resolution for unmatched games
    if unmatched and not args.no_prompt and not args.dry_run:
        print()
        print("─" * 62)
        print(f"  {len(unmatched)} game(s) need a category")
        print("─" * 62)

        valid_categories = sorted(core.CATEGORY_TO_COLLECTION.keys())
        still_unmatched = []

        for app_id, name in sorted(unmatched, key=lambda x: x[1].lower()):
            print(f"\n{name}")
            suggestion, genres = core.genre_suggestion(app_id)
            if genres:
                print(f"  Steam genres: {', '.join(genres)}")

            print("  Categories:", ", ".join(
                f"[{i}] {c}" for i, c in enumerate(valid_categories, 1)
            ))

            if suggestion:
                prompt = f"  Suggested: {suggestion} — press Enter to accept, type a number, or 's' to skip: "
            else:
                prompt = "  Type a number to categorize, or 's' to skip: "

            choice = input(prompt).strip()

            if choice == "" and suggestion:
                chosen = suggestion
            elif choice.lower() == "s":
                still_unmatched.append((app_id, name))
                continue
            elif choice.isdigit() and 1 <= int(choice) <= len(valid_categories):
                chosen = valid_categories[int(choice) - 1]
            else:
                print("  Not understood — skipping.")
                still_unmatched.append((app_id, name))
                continue

            to_add.setdefault(chosen, []).append(app_id)
            core.save_learned(core.CATEGORIES_FILE_DEFAULT, name, chosen)
            print(f"  ✓ Saved: {name} → {core.CATEGORY_TO_COLLECTION.get(chosen, chosen)}")

        unmatched = still_unmatched

    # Summary
    total_assigned = sum(len(v) for v in to_add.values())
    print()
    print("─" * 62)
    print(f"  Assigned:   {total_assigned}")
    print(f"  Soundtracks:{len(soundtracks)}")
    print(f"  Unmatched:  {len(unmatched)}")
    print("─" * 62)

    if unmatched:
        print("\nUnmatched (left uncategorized):")
        for aid, name in sorted(unmatched, key=lambda x: x[1].lower()):
            print(f"  [{aid}] {name}")

    # Compute removals: when a game's new category differs from a collection
    # it's already sitting in (among script-managed collections), remove it
    # from the old one so it doesn't end up duplicated across categories.
    removals = {}  # collection_display -> set of app_ids to remove
    managed_displays = set(core.CATEGORY_TO_COLLECTION.values())

    if args.overwrite:
        for category_key, app_ids in to_add.items():
            target_display = core.CATEGORY_TO_COLLECTION.get(category_key)
            if not target_display:
                continue
            for app_id in app_ids:
                for coll_name, info in collections.items():
                    if coll_name == target_display:
                        continue
                    if coll_name not in managed_displays:
                        continue
                    if app_id in info["added"]:
                        removals.setdefault(coll_name, set()).add(app_id)

    if removals:
        print("\nMoving games out of old categories:")
        for coll_name, ids in removals.items():
            print(f"  {coll_name}: -{len(ids)} games")

    if args.dry_run:
        print("\n[DRY RUN] Nothing written.")
        return

    # Apply to JSON
    next_version = max_version + 1

    # Apply removals first
    for coll_name, ids in removals.items():
        info = collections[coll_name]
        entry_idx = info["idx"]
        new_ids = info["added"] - ids
        val_obj = json.loads(data[entry_idx][1].get("value", "{}"))
        val_obj["added"] = sorted(new_ids)
        val_obj.pop("removed", None)
        data[entry_idx][1]["value"]     = json.dumps(val_obj)
        data[entry_idx][1]["timestamp"] = int(datetime.now().timestamp())
        data[entry_idx][1]["version"]   = str(next_version)
        next_version += 1
        # Keep our in-memory view consistent for the add pass below
        collections[coll_name]["added"] = new_ids

    for category_key, app_ids in to_add.items():
        if not app_ids:
            continue

        collection_display = core.CATEGORY_TO_COLLECTION.get(category_key)
        if not collection_display:
            continue

        if collection_display in collections:
            # Update existing collection
            entry_idx = collections[collection_display]["idx"]
            cid       = collections[collection_display]["id"]
            existing  = collections[collection_display]["added"]
            new_ids   = existing | set(app_ids)

            val_obj = json.loads(data[entry_idx][1].get("value", "{}"))
            val_obj["added"] = sorted(new_ids)
            val_obj.pop("removed", None)

            data[entry_idx][1]["value"]     = json.dumps(val_obj)
            data[entry_idx][1]["timestamp"] = int(datetime.now().timestamp())
            data[entry_idx][1]["version"]   = str(next_version)
            next_version += 1
            print(f"  Updated '{collection_display}': +{len(app_ids)} games")
        else:
            # Create new collection
            import uuid
            cid     = str(uuid.uuid4())[:8]
            val_obj = {
                "id":      cid,
                "name":    collection_display,
                "added":   sorted(app_ids),
                "removed": [],
            }
            new_entry = [
                f"user-collections.{cid}",
                {
                    "key":                    f"user-collections.{cid}",
                    "timestamp":              int(datetime.now().timestamp()),
                    "value":                  json.dumps(val_obj),
                    "version":                str(next_version),
                    "conflictResolutionMethod": "custom",
                    "strMethodId":            "union-collections",
                }
            ]
            data.append(new_entry)
            next_version += 1
            print(f"  Created '{collection_display}': {len(app_ids)} games")

    with open(CLOUD_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))

    print(f"\n✓ Done. Restart Steam for changes to appear.")
    print(f"  Backup is in the same folder if you need to roll back.")
    print()


if __name__ == "__main__":
    main()
