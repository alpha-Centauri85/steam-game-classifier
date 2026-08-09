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
import shutil
import argparse
import requests
from pathlib import Path
from datetime import datetime

# ── PATHS ─────────────────────────────────────────────────────────────────────
DEFAULT_STEAM_PATHS = [
    Path("C:/Program Files (x86)/Steam"),
    Path("C:/Program Files/Steam"),
    Path.home() / "Steam",
    Path.home() / ".steam" / "steam",
]

def find_cloud_json(steam_path_override=None):
    """Auto-detect cloud-storage-namespace-1.json for any Steam install."""
    search = [Path(steam_path_override)] if steam_path_override else DEFAULT_STEAM_PATHS
    for steam in search:
        userdata = steam / "userdata"
        if not userdata.exists():
            continue
        users = [d for d in userdata.iterdir()
                 if d.is_dir() and d.name.isdigit() and d.name != "0"]
        if not users:
            continue
        if len(users) > 1:
            print("Multiple Steam accounts found:")
            for i, u in enumerate(users):
                print(f"  {i+1}. Steam ID {u.name}")
            idx = int(input("Select account number: ")) - 1
            user = users[idx]
        else:
            user = users[0]
        cloud = user / "config" / "cloudstorage" / "cloud-storage-namespace-1.json"
        if cloud.exists():
            print(f"Steam user:  {user.name}")
            print(f"Cloud file:  {cloud}")
            return cloud
    raise FileNotFoundError(
        "Could not find cloud-storage-namespace-1.json.\n"
        "Use --steam-path to specify your Steam folder, e.g. --steam-path \"D:/Steam\""
    )


# ── EXTERNAL CATEGORY OVERRIDES ────────────────────────────────────────────────
# categories.json sits next to this script. New games learned interactively
# (or added by hand) live here, so the script itself never needs editing.
CATEGORIES_FILE = Path(__file__).parent / "categories.json"

def load_custom_categories():
    if CATEGORIES_FILE.exists():
        try:
            with open(CATEGORIES_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: could not read categories.json ({e}) — starting fresh.")
    return {}

def save_custom_category(name, category):
    custom = load_custom_categories()
    custom[name.lower().strip()] = category
    with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
        json.dump(custom, f, indent=2, ensure_ascii=False, sort_keys=True)


# ── STEAM GENRE LOOKUP (for suggestions) ──────────────────────────────────────
GENRE_TO_CATEGORY = {
    "action":            "ACTION/ADVENTURE",
    "adventure":         "ACTION/ADVENTURE",
    "rpg":               "JRPG",
    "role-playing":      "JRPG",
    "strategy":          "GRAND STRATEGY",
    "simulation":        "SIMULATION",
    "sports":            "SPORTS",
    "racing":            "SPORTS",
    "fighting":          "FIGHTING",
    "massively multiplayer": "MMO",
    "free to play":      None,   # not informative on its own
    "indie":             None,
    "casual":            None,
    "early access":      None,
}

def get_steam_genre_suggestion(app_id):
    """Fetch genres from Steam store API and map to a suggested category."""
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&filters=genres,categories"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get(str(app_id), {})
        if not data.get("success"):
            return None, []
        genres = [g["description"] for g in data["data"].get("genres", [])]
        for g in genres:
            mapped = GENRE_TO_CATEGORY.get(g.lower())
            if mapped:
                return mapped, genres
        return None, genres
    except Exception:
        return None, []

# ── COLLECTION NAME MAP ───────────────────────────────────────────────────────
# Maps the category strings used in GAME_CATEGORIES below
# to the exact display names of your Steam collections.
CATEGORY_TO_COLLECTION = {
    "ARPG":                 "ARPG",
    "CRPG":                 "CRPG",
    "JRPG":                 "JRPG",
    "MMO":                  "MMO",
    "LOOTER SHOOTER":       "Looter Shooter",
    "FPS":                  "FPS",
    "GRAND STRATEGY":       "Grand Strategy",
    "TURN BASED STRATEGY":  "Turn Based Strategy",
    "RTS":                  "RTS",
    "MANAGEMENT/TYCOON":    "Management/Tycoon",
    "SIMULATION":           "Simulation",
    "SANDBOX/SURVIVAL":     "Sandbox/Survival",
    "TOWER DEFENCE":        "Tower Defence",
    "PUZZLE&PLATFORM":      "Puzzle&Platform",
    "ACTION/ADVENTURE":     "Action/Adventure",
    "BATTLE WARFARE":       "Battle Warfare",
    "LEGO":                 "Lego",
    "STAR WARS":            "Star Wars",
    "CO-OP":                "Co-Op",
    "HACK & SLASH":         "Hack & Slash",
    "IDLE":                 "Idle",
    "SOUNDTRACKS":          "Soundtracks",
    "ACTION ROGUELITE":     "ACTION ROGUELITE",
    "SPORTS":               "Sports",
    "FIGHTING":             "Fighting",
    "DEMO":                 "Demo's",
    "MOBA":                 "MOBA",
}

# ── GAME → CATEGORY MAP ───────────────────────────────────────────────────────
GAME_CATEGORIES = {
    # ARPG
    "warframe":                                             "ARPG",
    "path of exile":                                        "ARPG",
    "path of exile 2":                                      "ARPG",
    "hero siege":                                           "ARPG",
    "torchlight":                                           "ARPG",
    "torchlight ii":                                        "ARPG",
    "torchlight iii":                                       "ARPG",
    "dark souls™: prepare to die edition":                  "HACK & SLASH",
    "dungeon siege":                                        "ARPG",
    "dungeon siege 2":                                      "ARPG",
    "dungeon siege iii":                                    "ARPG",
    "hades":                                                "ACTION ROGUELITE",
    "hades ii":                                             "ACTION ROGUELITE",
    "nuclear throne":                                       "ACTION ROGUELITE",
    "transistor":                                           "HACK & SLASH",
    "magicka":                                              "HACK & SLASH",
    # CRPG
    "baldur's gate 3":                                      "CRPG",
    "baldur's gate ii: enhanced edition":                   "CRPG",
    "mass effect 2 (2010)":                                 "CRPG",
    "mass effect 2 (2010) edition":                         "CRPG",
    "the elder scrolls v: skyrim":                          "CRPG",
    "the elder scrolls v: skyrim special edition":          "CRPG",
    "the elder scrolls iv: oblivion game of the year edition (2009)": "CRPG",
    "fable iii":                                            "CRPG",
    "the witcher 3: wild hunt":                             "CRPG",
    "pillars of eternity ii: deadfire":                     "CRPG",
    "divinity: original sin enhanced edition":              "CRPG",
    "divinity: original sin 2":                             "CRPG",
    "divinity: original sin (classic)":                     "CRPG",
    "fallout 4":                                            "CRPG",
    "icewind dale: enhanced edition":                       "CRPG",
    "avadon: the black fortress":                           "CRPG",
    "divine divinity":                                      "CRPG",
    "beyond divinity":                                      "CRPG",
    # JRPG
    "final fantasy":                                        "JRPG",
    "final fantasy ii":                                     "JRPG",
    "final fantasy iii":                                    "JRPG",
    "final fantasy iv":                                     "JRPG",
    "final fantasy v":                                      "JRPG",
    "final fantasy vi":                                     "JRPG",
    "final fantasy vii (2013)":                             "JRPG",
    "final fantasy vii":                                    "JRPG",
    "final fantasy vii remake intergrade":                  "JRPG",
    "final fantasy vii rebirth":                            "JRPG",
    "final fantasy viii":                                   "JRPG",
    "final fantasy viii - remastered":                      "JRPG",
    "final fantasy ix":                                     "JRPG",
    "final fantasy x/x-2 hd remaster":                     "JRPG",
    "final fantasy xii the zodiac age":                     "JRPG",
    "final fantasy xiii":                                   "JRPG",
    "final fantasy xiii-2":                                 "JRPG",
    "lightning returns: final fantasy xiii":                "JRPG",
    "final fantasy xv windows edition":                     "JRPG",
    "final fantasy xvi":                                    "JRPG",
    "final fantasy type-0 hd":                              "JRPG",
    "final fantasy iv (3d remake)":                         "JRPG",
    "final fantasy iii (3d remake)":                        "JRPG",
    "final fantasy® xi: ultimate collection seekers edition row": "MMO",
    "octopath traveler":                                    "JRPG",
    "octopath traveler ii":                                 "JRPG",
    "sea of stars: sunset edition":                         "JRPG",
    "sea of stars":                                         "JRPG",
    "ni no kuni™ ii: revenant kingdom":                     "JRPG",
    "i am setsuna":                                         "JRPG",
    "the legend of heroes: trails in the sky":              "JRPG",
    "agarest: generations of war":                          "JRPG",
    "the last remnant":                                     "JRPG",
    "recettear: an item shop's tale":                       "JRPG",
    "undertale":                                            "JRPG",
    "evoland legendary edition":                            "JRPG",
    "evoland 2":                                            "JRPG",
    "valkyria chronicles™":                                 "JRPG",
    "superbrothers: sword & sworcery ep":                   "JRPG",
    "sakura spirit":                                        "JRPG",
    "dragon ball xenoverse":                                "JRPG",
    "bastion":                                              "HACK & SLASH",
    # MMO
    "final fantasy xiv online":                             "MMO",
    "guild wars 2®":                                        "MMO",
    "guild wars 2":                                         "MMO",
    "lost ark":                                             "MMO",
    "tera":                                                 "MMO",
    "black desert":                                         "MMO",
    "trove":                                                "MMO",
    "riders of icarus":                                     "MMO",
    "rusty hearts":                                         "MMO",
    # LOOTER SHOOTER
    "borderlands goty":                                     "LOOTER SHOOTER",
    "borderlands 2":                                        "LOOTER SHOOTER",
    "borderlands: the pre-sequel":                          "LOOTER SHOOTER",
    "borderlands goty enhanced":                            "LOOTER SHOOTER",
    "helldivers™ 2":                                        "LOOTER SHOOTER",
    "helldivers 2":                                         "LOOTER SHOOTER",
    "tom clancy's the division":                            "LOOTER SHOOTER",
    "destiny 2":                                            "LOOTER SHOOTER",
    # FPS
    "call of duty: black ops":                              "FPS",
    "call of duty: black ops - multiplayer":                "FPS",
    "call of duty: black ops ii":                           "FPS",
    "call of duty: black ops ii - multiplayer":             "FPS",
    "call of duty: black ops ii - zombies":                 "FPS",
    "call of duty®: modern warfare® 3 (2011)":              "FPS",
    "call of duty®: modern warfare® 3 (2011) - multiplayer": "FPS",
    "half-life 2":                                          "FPS",
    "half-life 2: deathmatch":                              "FPS",
    "half-life: source":                                    "FPS",
    "half-life deathmatch: source":                         "FPS",
    "quake":                                                "FPS",
    "quake ii":                                             "FPS",
    "quake ii: ground zero":                                "FPS",
    "quake ii: the reckoning":                              "FPS",
    "quake iii arena":                                      "FPS",
    "quake iii: team arena":                                "FPS",
    "quake mission pack 1: scourge of armagon":             "FPS",
    "quake mission pack 2: dissolution of eternity":        "FPS",
    "serious sam 3: bfe":                                   "FPS",
    "serious sam fusion 2017 (beta)":                       "FPS",
    "counter-strike: source":                               "FPS",
    "counter-strike 2":                                     "FPS",
    "wolfenstein: the new order":                           "FPS",
    "crysis 2 maximum edition":                             "FPS",
    "far cry 2":                                            "FPS",
    "far cry":                                              "FPS",
    "call of juarez":                                       "FPS",
    "medal of honor(tm) multiplayer":                       "FPS",
    "medal of honor(tm) single player":                     "FPS",
    "spec ops: the line":                                   "FPS",
    "payday 2":                                             "FPS",
    "left 4 dead 2":                                        "FPS",
    "natural selection 2":                                  "FPS",
    "ace of spades":                                        "FPS",
    "bioshock":                                             "FPS",
    "bioshock remastered":                                  "FPS",
    "bioshock 2":                                           "FPS",
    "bioshock 2 remastered":                                "FPS",
    "bioshock infinite":                                    "FPS",
    # GRAND STRATEGY
    "sid meier's civilization iii: complete":               "GRAND STRATEGY",
    "sid meier's civilization iv":                          "GRAND STRATEGY",
    "sid meier's civilization v":                           "GRAND STRATEGY",
    "sid meier's civilization vi":                          "GRAND STRATEGY",
    "sid meier's civilization: beyond earth":               "GRAND STRATEGY",
    "crusader kings ii":                                    "GRAND STRATEGY",
    "hearts of iron iv":                                    "GRAND STRATEGY",
    "stellaris":                                            "GRAND STRATEGY",
    "defcon":                                               "GRAND STRATEGY",
    "defcon beta demo":                                     "GRAND STRATEGY",
    "sword of the stars ii: enhanced edition":              "GRAND STRATEGY",
    # TURN BASED STRATEGY
    "endless legend™":                                      "TURN BASED STRATEGY",
    "endless legend":                                       "TURN BASED STRATEGY",
    "heroes of might & magic iii - hd edition":             "TURN BASED STRATEGY",
    "might & magic: heroes vi":                             "TURN BASED STRATEGY",
    "pit people":                                           "TURN BASED STRATEGY",
    "magic 2015":                                           "TURN BASED STRATEGY",
    # RTS
    "command & conquer™ remastered collection":             "RTS",
    "command & conquer™ red alert™ 3 - uprising":           "RTS",
    "age of empires ii (2013)":                             "RTS",
    "age of empires® iii (2007)":                           "RTS",
    "rise of nations: extended edition":                    "RTS",
    "ashes of the singularity: classic":                    "RTS",
    "ashes of the singularity: escalation":                 "RTS",
    "stronghold crusader hd":                               "RTS",
    "stronghold crusader extreme hd":                       "RTS",
    "warhammer 40,000: dawn of war - anniversary edition":  "RTS",
    "warhammer 40,000: dawn of war - soulstorm":            "RTS",
    "warhammer 40,000: dawn of war - dark crusade":         "RTS",
    "warhammer 40,000: dawn of war - winter assault":       "RTS",
    "gratuitous space battles":                             "RTS",
    "darwinia":                                             "RTS",
    # MANAGEMENT/TYCOON
    "rollercoaster tycoon 3: platinum!":                    "MANAGEMENT/TYCOON",
    "cities: skylines":                                     "MANAGEMENT/TYCOON",
    "big pharma":                                           "MANAGEMENT/TYCOON",
    "parkitect":                                            "MANAGEMENT/TYCOON",
    "planet coaster":                                       "MANAGEMENT/TYCOON",
    "simcity 4 deluxe":                                     "MANAGEMENT/TYCOON",
    "jurassic world evolution":                             "MANAGEMENT/TYCOON",
    "tropico 5":                                            "MANAGEMENT/TYCOON",
    "project hospital":                                     "MANAGEMENT/TYCOON",
    "plague inc: evolved":                                  "MANAGEMENT/TYCOON",
    "cities in motion 2":                                   "MANAGEMENT/TYCOON",
    "cook, serve, delicious!":                              "MANAGEMENT/TYCOON",
    "plateup!":                                             "MANAGEMENT/TYCOON",
    "revolution idle":                                      "MANAGEMENT/TYCOON",
    # SIMULATION
    "farming simulator 25":                                 "SIMULATION",
    "wallpaper engine":                                     "SIMULATION",
    "pc building simulator":                                "SIMULATION",
    "universe sandbox legacy":                              "SIMULATION",
    "kerbal space program":                                 "SIMULATION",
    "euro truck simulator 2":                               "SIMULATION",
    "euro truck simulator":                                 "SIMULATION",
    "scania truck driving simulator":                       "SIMULATION",
    "trucks & trailers":                                    "SIMULATION",
    "bus driver":                                           "SIMULATION",
    "need for speed: shift":                                "SPORTS",
    "f1 2013":                                              "SPORTS",
    "burnout paradise: the ultimate box":                   "SIMULATION",
    "asphalt legends":                                      "SIMULATION",
    "3dmark":                                               "SIMULATION",
    "rocket league":                                        "SPORTS",
    # SANDBOX/SURVIVAL
    "terraria":                                             "SANDBOX/SURVIVAL",
    "valheim":                                              "SANDBOX/SURVIVAL",
    "no man's sky":                                         "SANDBOX/SURVIVAL",
    "ark: survival evolved":                                "SANDBOX/SURVIVAL",
    "ark: survival of the fittest":                         "SANDBOX/SURVIVAL",
    "space engineers":                                      "SANDBOX/SURVIVAL",
    "besiege":                                              "SANDBOX/SURVIVAL",
    "the planet crafter":                                   "SANDBOX/SURVIVAL",
    "shapez 2 - factory":                                   "SANDBOX/SURVIVAL",
    "stardew valley":                                       "SANDBOX/SURVIVAL",
    "garry's mod":                                          "SANDBOX/SURVIVAL",
    "totally accurate battle simulator":                    "SANDBOX/SURVIVAL",
    "goat simulator":                                       "SANDBOX/SURVIVAL",
    "eufloria":                                             "SANDBOX/SURVIVAL",
    "eufloria hd":                                          "SANDBOX/SURVIVAL",
    "x: beyond the frontier":                               "SANDBOX/SURVIVAL",
    "x-tension":                                            "SANDBOX/SURVIVAL",
    "x2: the threat":                                       "SANDBOX/SURVIVAL",
    "x3: terran conflict":                                  "SANDBOX/SURVIVAL",
    "x3: reunion":                                          "SANDBOX/SURVIVAL",
    "x3: albion prelude":                                   "SANDBOX/SURVIVAL",
    # TOWER DEFENCE
    "orcs must die!":                                       "TOWER DEFENCE",
    "orcs must die! 2":                                     "TOWER DEFENCE",
    "sanctum":                                              "TOWER DEFENCE",
    "sanctum 2":                                            "TOWER DEFENCE",
    "revenge of the titans":                                "TOWER DEFENCE",
    # PUZZLE&PLATFORM
    "portal":                                               "PUZZLE&PLATFORM",
    "portal 2":                                             "PUZZLE&PLATFORM",
    "aperture tag: the paint gun testing initiative":       "PUZZLE&PLATFORM",
    "ori and the blind forest":                             "PUZZLE&PLATFORM",
    "hollow knight":                                        "PUZZLE&PLATFORM",
    "limbo":                                                "PUZZLE&PLATFORM",
    "braid":                                                "PUZZLE&PLATFORM",
    "super meat boy":                                       "PUZZLE&PLATFORM",
    "vvvvvv":                                               "PUZZLE&PLATFORM",
    "mark of the ninja":                                    "PUZZLE&PLATFORM",
    "hexcells":                                             "PUZZLE&PLATFORM",
    "hexcells plus":                                        "PUZZLE&PLATFORM",
    "hexcells infinite":                                    "PUZZLE&PLATFORM",
    "bridge constructor":                                   "PUZZLE&PLATFORM",
    "machinarium":                                          "PUZZLE&PLATFORM",
    "thomas was alone":                                     "PUZZLE&PLATFORM",
    "outland":                                              "PUZZLE&PLATFORM",
    "contraption maker":                                    "PUZZLE&PLATFORM",
    "cogs":                                                 "PUZZLE&PLATFORM",
    "zen bound® 2":                                         "PUZZLE&PLATFORM",
    "rochard":                                              "PUZZLE&PLATFORM",
    "shatter":                                              "PUZZLE&PLATFORM",
    "titan attacks":                                        "PUZZLE&PLATFORM",
    "dinocide":                                             "PUZZLE&PLATFORM",
    "oozi: earth adventure":                                "PUZZLE&PLATFORM",
    "super time force ultra":                               "PUZZLE&PLATFORM",
    "bit.trip runner":                                      "PUZZLE&PLATFORM",
    "bit.trip presents... runner2: future legend of rhythm alien": "PUZZLE&PLATFORM",
    "nights into dreams...":                                "PUZZLE&PLATFORM",
    "regency solitaire":                                    "PUZZLE&PLATFORM",
    "gomo":                                                 "PUZZLE&PLATFORM",
    "back to bed":                                          "PUZZLE&PLATFORM",
    "ink":                                                  "PUZZLE&PLATFORM",
    "toyodyssey":                                           "PUZZLE&PLATFORM",
    "trine 2":                                              "PUZZLE&PLATFORM",
    "vessel":                                               "PUZZLE&PLATFORM",
    "snuggle truck":                                        "PUZZLE&PLATFORM",
    "solstice":                                             "PUZZLE&PLATFORM",
    "the whispered world special edition":                  "PUZZLE&PLATFORM",
    "the night of the rabbit":                              "PUZZLE&PLATFORM",
    "day of the tentacle remastered":                       "PUZZLE&PLATFORM",
    "the beginner's guide":                                 "PUZZLE&PLATFORM",
    "psychonauts":                                          "PUZZLE&PLATFORM",
    "not the robots":                                       "PUZZLE&PLATFORM",
    "montas":                                               "PUZZLE&PLATFORM",
    "life is strange™":                                     "PUZZLE&PLATFORM",
    "life is strange":                                      "PUZZLE&PLATFORM",
    # ACTION/ADVENTURE
    "grand theft auto v legacy":                            "ACTION/ADVENTURE",
    "grand theft auto v enhanced":                          "ACTION/ADVENTURE",
    "assassin's creed ii":                                  "ACTION/ADVENTURE",
    "assassin's creed":                                     "ACTION/ADVENTURE",
    "just cause 2":                                         "ACTION/ADVENTURE",
    "just cause 3":                                         "ACTION/ADVENTURE",
    "hogwarts legacy":                                      "ACTION/ADVENTURE",
    "batman: arkham city goty":                             "ACTION/ADVENTURE",
    "tomb raider":                                          "ACTION/ADVENTURE",
    "darksiders":                                           "ACTION/ADVENTURE",
    "darksiders warmastered edition":                       "ACTION/ADVENTURE",
    "darksiders ii":                                        "ACTION/ADVENTURE",
    "darksiders ii deathinitive edition":                   "ACTION/ADVENTURE",
    "metal gear rising: revengeance":                       "ACTION/ADVENTURE",
    "devil may cry 4":                                      "ACTION/ADVENTURE",
    "mirror's edge":                                        "ACTION/ADVENTURE",
    "prince of persia: the sands of time":                  "ACTION/ADVENTURE",
    "prince of persia: the forgotten sands":                "ACTION/ADVENTURE",
    "dead space (2008)":                                    "ACTION/ADVENTURE",
    "sleeping dogs: definitive edition":                    "ACTION/ADVENTURE",
    "watch_dogs":                                           "ACTION/ADVENTURE",
    "amnesia: the dark descent":                            "ACTION/ADVENTURE",
    "kholat":                                               "ACTION/ADVENTURE",
    "lone survivor: the director's cut":                    "ACTION/ADVENTURE",
    "the vanishing of ethan carter":                        "ACTION/ADVENTURE",
    "the vanishing of ethan carter redux":                  "ACTION/ADVENTURE",
    "uncanny valley":                                       "ACTION/ADVENTURE",
    "home":                                                 "ACTION/ADVENTURE",
    "galaxy on fire 2™ full hd":                            "ACTION/ADVENTURE",
    "strike suit zero":                                     "ACTION/ADVENTURE",
    "strike suit infinity":                                 "ACTION/ADVENTURE",
    "galak-z":                                              "ACTION/ADVENTURE",
    "everspace™":                                           "ACTION/ADVENTURE",
    "everspace":                                            "ACTION/ADVENTURE",
    "tom clancy's h.a.w.x. 2":                             "ACTION/ADVENTURE",
    "vector thrust":                                        "ACTION/ADVENTURE",
    "halo: spartan assault":                                "ACTION/ADVENTURE",
    "shadwen":                                              "ACTION/ADVENTURE",
    "thief":                                                "ACTION/ADVENTURE",
    "thief gold":                                           "ACTION/ADVENTURE",
    "thief™ ii: the metal age":                             "ACTION/ADVENTURE",
    "thief: deadly shadows":                                "ACTION/ADVENTURE",
    "guns of icarus online":                                "ACTION/ADVENTURE",
    "space pirates and zombies":                            "ACTION/ADVENTURE",
    "choplifter hd":                                        "ACTION/ADVENTURE",
    "droid assault":                                        "ACTION/ADVENTURE",
    "ion assault":                                          "ACTION/ADVENTURE",
    "ultratron":                                            "ACTION/ADVENTURE",
    "lara croft and the temple of osiris":                  "ACTION/ADVENTURE",
    "battleborn":                                           "ACTION/ADVENTURE",
    "brawlhalla":                                           "FIGHTING",
    "lethal league":                                        "FIGHTING",
    "blazblue: calamity trigger":                           "FIGHTING",
    "guilty gear xx accent core plus r":                    "FIGHTING",
    "plain sight":                                          "ACTION/ADVENTURE",
    "jamestown":                                            "ACTION/ADVENTURE",
    "swords and soldiers hd":                               "ACTION/ADVENTURE",
    "paladins":                                             "ACTION/ADVENTURE",
    "awesomenauts":                                         "ACTION/ADVENTURE",
    # BATTLE WARFARE
    "warhammer: vermintide 2":                              "BATTLE WARFARE",
    # LEGO
    "lego® star wars™: the skywalker saga":                 "LEGO",
    "lego® batman™: the videogame":                         "LEGO",
    "lego® star wars™ iii: the clone wars™":                "LEGO",
    "lego® star wars™: the complete saga":                  "LEGO",
    "lego® marvel super heroes":                            "LEGO",
    "lego® marvel's avengers":                              "LEGO",
    "lego® harry potter: years 1-4":                        "LEGO",
    "lego® harry potter: years 5-7":                        "LEGO",
    "lego® the hobbit™":                                    "LEGO",
    "lego® the lord of the rings™":                         "LEGO",
    # IDLE
    "revolution idle":                                      "IDLE",
    "cookie clicker":                                       "IDLE",
    "clicker heroes":                                       "IDLE",
    "realm grinder":                                        "IDLE",
    "adventure capitalist":                                 "IDLE",
    "time clickers":                                        "IDLE",
    "kittens game":                                         "IDLE",
    # ACTION ROGUELITE
    "megabonk":                                             "ACTION ROGUELITE",
    "hades":                                                "ACTION ROGUELITE",
    "hades ii":                                             "ACTION ROGUELITE",
    "nuclear throne":                                       "ACTION ROGUELITE",
    "ravenswatch":                                          "ACTION ROGUELITE",
    "vampire survivors":                                    "ACTION ROGUELITE",
    "dead cells":                                           "ACTION ROGUELITE",
    "risk of rain 2":                                       "ACTION ROGUELITE",
    "noita":                                                "ACTION ROGUELITE",
    # SPORTS
    "f1 2013":                                              "SPORTS",
    "rocket league":                                        "SPORTS",
    "need for speed: shift":                                "SPORTS",
    "ea sports fc™ 26":                                    "SPORTS",
    "ea sports fc 26":                                      "SPORTS",
    "f1 24":                                                "SPORTS",
    "f1 23":                                                "SPORTS",
    # FIGHTING
    "granblue fantasy versus: rising":                      "FIGHTING",
    "guilty gear strive":                                   "FIGHTING",
    "street fighter 6":                                     "FIGHTING",
    "dragon ball fighterz":                                 "FIGHTING",
    "under night in-birth ii sys:cclr":                     "FIGHTING",
    # DEMO
    "defcon beta demo":                                     "DEMO",
    "octopath traveler 0 prologue demo":                    "DEMO",
    "vessel demo":                                          "DEMO",
    "waterpark simulator demo":                             "DEMO",
    "ark: survival of the fittest":                         "DEMO",
    # NEW GAMES
    "scarlet nexus":                                        "ARPG",
    "titanfall® 2":                                        "FPS",
    "titanfall 2":                                          "FPS",
    "granblue fantasy: relink":                             "ARPG",
    "granblue fantasy relink":                              "ARPG",
    "romestead":                                            "SANDBOX/SURVIVAL",
    "thehunter: call of the wild™":                         "SIMULATION",
    "thehunter: call of the wild":                          "SIMULATION",
    "palworld":                                              "SANDBOX/SURVIVAL",
    "dota 2":                                                "MOBA",
    "cooking simulator":                                     "MANAGEMENT/TYCOON",
    "house flipper 2":                                       "SIMULATION",
    "dustforce":                                              "PUZZLE&PLATFORM",
    "wizorb":                                                "PUZZLE&PLATFORM",
    "the undergarden":                                        "PUZZLE&PLATFORM",
    "tom clancy's the division pts":                          "DEMO",
    # STAR WARS
    "star wars™ republic commando":                         "STAR WARS",
    "star wars™ jedi knight: dark forces ii":               "STAR WARS",
    "star wars™ jedi knight: mysteries of the sith™":       "STAR WARS",
    "star wars™ jedi knight ii: jedi outcast™":             "STAR WARS",
    "star wars™ jedi knight: jedi academy™":                "STAR WARS",
    "star wars™: the force unleashed™ ultimate sith edition": "STAR WARS",
    "star wars™ empire at war: gold pack":                  "STAR WARS",
    "star wars™ galactic battlegrounds saga":               "STAR WARS",
    "star wars™ knights of the old republic™":              "STAR WARS",
    "star wars™ knights of the old republic™ ii: the sith lords™": "STAR WARS",
    "star wars™ rebellion":                                 "STAR WARS",
    "star wars™ starfighter™":                              "STAR WARS",
    "star wars™ x-wing vs tie fighter: balance of power campaigns™": "STAR WARS",
    "star wars™: rebel assault i + ii":                     "STAR WARS",
    "star wars™: rogue squadron 3d":                        "STAR WARS",
    "star wars™: the clone wars - republic heroes™":        "STAR WARS",
    "star wars™: the force unleashed™ ii":                  "STAR WARS",
    "star wars™: tie fighter special edition":              "STAR WARS",
    "star wars™: x-wing alliance™":                         "STAR WARS",
    "star wars™: x-wing special edition":                   "STAR WARS",
    "star wars™: dark forces":                              "STAR WARS",
    "star wars: battlefront 2 (classic, 2005)":             "STAR WARS",
    # CO-OP
    "overcooked! 2":                                        "CO-OP",
    "golf with your friends":                               "CO-OP",
    "rv there yet?":                                        "CO-OP",
    "vinebound: tangled together":                          "CO-OP",
    "frog climbers":                                        "CO-OP",
    "lovers in a dangerous spacetime":                      "CO-OP",
    "tabletop simulator":                                   "CO-OP",
    "octodad: dadliest catch":                              "CO-OP",
    # HACK & SLASH (separate from ARPG)
    "darksiders":                                           "HACK & SLASH",
    "darksiders warmastered edition":                       "HACK & SLASH",
    "darksiders ii":                                        "HACK & SLASH",
    "darksiders ii deathinitive edition":                   "HACK & SLASH",
    "devil may cry 4":                                      "HACK & SLASH",
    "metal gear rising: revengeance":                       "HACK & SLASH",
}

PARTIAL_MATCH_RULES = [
    ("star wars",         "STAR WARS"),
    ("final fantasy",     "JRPG"),
    ("lego®",             "LEGO"),
    ("lego ",             "LEGO"),
    ("civilization",      "GRAND STRATEGY"),
    ("call of duty",      "FPS"),
    ("half-life",         "FPS"),
    ("bioshock",          "FPS"),
    ("quake",             "FPS"),
    ("borderlands",       "LOOTER SHOOTER"),
    ("darksiders",        "HACK & SLASH"),
    ("dungeon siege",     "ARPG"),
    ("divinity:",         "CRPG"),
    ("euro truck",        "SIMULATION"),
    ("warhammer 40,000",  "RTS"),
    ("age of empires",    "RTS"),
    ("assassin's creed",  "ACTION/ADVENTURE"),
    ("torchlight",        "ARPG"),
]


# ── HELPERS ───────────────────────────────────────────────────────────────────

def backup(path):
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = path.parent / f"{path.stem}_backup_{ts}{path.suffix}"
    shutil.copy2(path, dst)
    print(f"✓ Backup: {dst.name}")
    return dst


def get_owned_games(api_key, steam_id):
    url = (
        "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        f"?key={api_key}&steamid={steam_id}&include_appinfo=1&format=json"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    games = r.json().get("response", {}).get("games", [])
    return {g["appid"]: g["name"] for g in games}


def categorize(name, custom=None):
    custom = custom or {}
    key = name.lower().strip()
    for suffix in [" (2010)", " (2013)", " (2008)", " (2005)", " (2007)", " (2009)"]:
        if key.endswith(suffix):
            key = key[:-len(suffix)]
    if key in custom:
        return custom[key]
    if key in GAME_CATEGORIES:
        return GAME_CATEGORIES[key]
    if name.lower().strip() in GAME_CATEGORIES:
        return GAME_CATEGORIES[name.lower().strip()]
    for partial, cat in PARTIAL_MATCH_RULES:
        if partial in key:
            return cat
    return None


def load_collections(data):
    """
    Returns:
        collections  dict: display_name → {id, added (set), entry_index}
        all_categorized set: all app IDs already in any collection
        max_version  int
    """
    collections     = {}
    all_categorized = set()
    max_version     = 0

    for idx, (k, v) in enumerate(data):
        if not k.startswith("user-collections"):
            continue
        if v.get("is_deleted"):
            continue
        try:
            val  = json.loads(v.get("value", "{}"))
            name = val.get("name", "")
            cid  = val.get("id", "")
            added = set(val.get("added", []))
            all_categorized |= added
            collections[name] = {
                "id":    cid,
                "added": added,
                "idx":   idx,
            }
            ver = int(v.get("version", "0"))
            if ver > max_version:
                max_version = ver
        except Exception:
            pass

    return collections, all_categorized, max_version


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

    custom_categories = load_custom_categories()
    if custom_categories:
        print(f"Loaded {len(custom_categories)} learned categories from categories.json")

    try:
        CLOUD_JSON = find_cloud_json(args.steam_path)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)

    if not args.dry_run:
        backup(CLOUD_JSON)
    else:
        print("  [DRY RUN — nothing will be written]")

    # Load JSON
    data = json.load(open(CLOUD_JSON, encoding="utf-8"))
    collections, already_categorized, max_version = load_collections(data)

    print(f"\nExisting collections: {len(collections)}")
    for name, info in sorted(collections.items()):
        print(f"  {name}: {len(info['added'])} games")

    # Fetch owned games
    print(f"\nFetching owned games from Steam API...")
    session = requests.Session()
    owned = get_owned_games(args.api_key, args.steam_id)
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
    coll_by_display = {v: k for k, v in CATEGORY_TO_COLLECTION.items()}

    # Track changes: category_key → list of app IDs to add
    to_add       = {cat: [] for cat in CATEGORY_TO_COLLECTION}
    unmatched    = []
    soundtracks  = []

    for app_id, name in sorted(to_process.items(), key=lambda x: x[1]):
        category = categorize(name, custom_categories)
        if category == "SOUNDTRACKS":
            soundtracks.append((app_id, name))
            to_add["SOUNDTRACKS"].append(app_id)
        elif category:
            to_add[category].append(app_id)
            print(f"  ✓ {name}  →  {CATEGORY_TO_COLLECTION.get(category, category)}")
        else:
            unmatched.append((app_id, name))

    # Interactive resolution for unmatched games
    if unmatched and not args.no_prompt and not args.dry_run:
        print()
        print("─" * 62)
        print(f"  {len(unmatched)} game(s) need a category")
        print("─" * 62)

        valid_categories = sorted(CATEGORY_TO_COLLECTION.keys())
        still_unmatched = []

        for app_id, name in sorted(unmatched, key=lambda x: x[1].lower()):
            print(f"\n{name}")
            suggestion, genres = get_steam_genre_suggestion(app_id)
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
            save_custom_category(name, chosen)
            print(f"  ✓ Saved: {name} → {CATEGORY_TO_COLLECTION.get(chosen, chosen)}")

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
    managed_displays = set(CATEGORY_TO_COLLECTION.values())

    if args.overwrite:
        for category_key, app_ids in to_add.items():
            target_display = CATEGORY_TO_COLLECTION.get(category_key)
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

        collection_display = CATEGORY_TO_COLLECTION.get(category_key)
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
