"""Core Steam game categorisation logic, extracted from steam_categorizer_v2.py."""

import json
import re
import shutil
import uuid
import requests  # default http
from datetime import datetime
from pathlib import Path

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


def valid_categories():
    return sorted(CATEGORY_TO_COLLECTION.keys())


def collection_display(category_key):
    return CATEGORY_TO_COLLECTION.get(category_key, category_key)


CATEGORIES_FILE_DEFAULT = Path(__file__).parent / "categories.json"


def load_learned(path):
    path = Path(path)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_learned(path, name, category):
    path = Path(path)
    learned = load_learned(path)
    learned[name.lower().strip()] = category
    with open(path, "w", encoding="utf-8") as f:
        json.dump(learned, f, indent=2, ensure_ascii=False, sort_keys=True)


class AmbiguousAccountError(Exception):
    pass


DEFAULT_STEAM_PATHS = [
    Path("C:/Program Files (x86)/Steam"),
    Path("C:/Program Files/Steam"),
    Path.home() / "Steam",
    Path.home() / ".steam" / "steam",
]


def list_steam_accounts(steam_path_override=None):
    search = [Path(steam_path_override)] if steam_path_override else DEFAULT_STEAM_PATHS
    accounts = []
    for steam in search:
        userdata = steam / "userdata"
        if not userdata.exists():
            continue
        for d in userdata.iterdir():
            if not (d.is_dir() and d.name.isdigit() and d.name != "0"):
                continue
            cloud = d / "config" / "cloudstorage" / "cloud-storage-namespace-1.json"
            if cloud.exists():
                accounts.append({"steam_id3": d.name, "cloud_json": cloud})
    return accounts


def find_cloud_json(steam_path_override=None, account_id3=None):
    accounts = list_steam_accounts(steam_path_override)
    if not accounts:
        raise FileNotFoundError(
            "Could not find cloud-storage-namespace-1.json. "
            "Set a custom Steam path, e.g. D:/Steam"
        )
    if account_id3:
        for a in accounts:
            if a["steam_id3"] == account_id3:
                return a["cloud_json"]
        raise FileNotFoundError(f"No Steam account {account_id3} found.")
    if len(accounts) > 1:
        raise AmbiguousAccountError([a["steam_id3"] for a in accounts])
    return accounts[0]["cloud_json"]


def is_steam_running():
    import subprocess, sys
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
                capture_output=True, text=True, timeout=5,
            )
            return "steam.exe" in out.stdout.lower()
        out = subprocess.run(["pgrep", "-x", "steam"], capture_output=True, timeout=5)
        return out.returncode == 0
    except Exception:
        return False


def get_owned_games(api_key, steam_id, http=requests):
    url = (
        "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
        f"?key={api_key}&steamid={steam_id}&include_appinfo=1&format=json"
    )
    r = http.get(url, timeout=15)
    r.raise_for_status()
    games = r.json().get("response", {}).get("games", [])
    return {g["appid"]: g["name"] for g in games}


def resolve_steam_id(api_key, profile_input, http=requests):
    text = profile_input.strip()
    m = re.search(r"/profiles/(\d{17})", text)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d{17}", text):
        return text
    m = re.search(r"/id/([^/]+)", text)
    vanity = m.group(1) if m else text
    url = (
        "http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
        f"?key={api_key}&vanityurl={vanity}"
    )
    r = http.get(url, timeout=15)
    r.raise_for_status()
    resp = r.json().get("response", {})
    if resp.get("success") == 1 and resp.get("steamid"):
        return resp["steamid"]
    raise ValueError("Could not find that profile.")


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


def _current_collection_for(app_id, collections):
    """Display name of the managed collection this app currently sits in, else None."""
    managed = set(CATEGORY_TO_COLLECTION.values())
    for name, info in collections.items():
        if name in managed and app_id in info["added"]:
            return name
    return None


def build_change_set(owned, data, learned=None, overwrite=False):
    learned = learned or {}
    collections, already_categorised, _ = load_collections(data)

    will_change, unknown = [], []
    no_change = 0

    for app_id, name in sorted(owned.items(), key=lambda x: x[1].lower()):
        current = _current_collection_for(app_id, collections)
        if app_id in already_categorised and not overwrite:
            no_change += 1
            continue

        category = categorize(name, learned)
        if category is None:
            if current is None:
                unknown.append({"app_id": app_id, "name": name})
            else:
                no_change += 1
            continue

        target_display = collection_display(category)
        if current == target_display:
            no_change += 1
            continue

        will_change.append({
            "app_id": app_id,
            "name": name,
            "from": current,
            "to": category,
            "to_display": target_display,
        })

    return {"will_change": will_change, "unknown": unknown, "no_change": no_change}


def backup(path):
    path = Path(path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = path.parent / f"{path.stem}_backup_{ts}{path.suffix}"
    shutil.copy2(path, dst)
    return dst


def apply_assignments(cloud_json_path, assignments, overwrite=False):
    cloud_json_path = Path(cloud_json_path)
    backup_path = backup(cloud_json_path)

    with open(cloud_json_path, encoding="utf-8") as f:
        data = json.load(f)
    collections, _, max_version = load_collections(data)
    next_version = max_version + 1
    managed_displays = set(CATEGORY_TO_COLLECTION.values())

    # Removals (overwrite only): pull each moved game out of other managed collections.
    removals = {}
    if overwrite:
        for category_key, app_ids in assignments.items():
            target_display = collection_display(category_key)
            for app_id in app_ids:
                for coll_name, info in collections.items():
                    if coll_name == target_display or coll_name not in managed_displays:
                        continue
                    if app_id in info["added"]:
                        removals.setdefault(coll_name, set()).add(app_id)

    for coll_name, ids in removals.items():
        info = collections[coll_name]
        new_ids = info["added"] - ids
        val_obj = json.loads(data[info["idx"]][1].get("value", "{}"))
        val_obj["added"] = sorted(new_ids)
        val_obj.pop("removed", None)
        data[info["idx"]][1]["value"] = json.dumps(val_obj)
        data[info["idx"]][1]["timestamp"] = int(datetime.now().timestamp())
        data[info["idx"]][1]["version"] = str(next_version)
        next_version += 1
        collections[coll_name]["added"] = new_ids

    created, updated, assigned = [], [], 0
    for category_key, app_ids in assignments.items():
        if not app_ids:
            continue
        display = collection_display(category_key)
        assigned += len(app_ids)
        if display in collections:
            info = collections[display]
            new_ids = info["added"] | set(app_ids)
            val_obj = json.loads(data[info["idx"]][1].get("value", "{}"))
            val_obj["added"] = sorted(new_ids)
            val_obj.pop("removed", None)
            data[info["idx"]][1]["value"] = json.dumps(val_obj)
            data[info["idx"]][1]["timestamp"] = int(datetime.now().timestamp())
            data[info["idx"]][1]["version"] = str(next_version)
            updated.append(display)
        else:
            cid = str(uuid.uuid4())[:8]
            val_obj = {"id": cid, "name": display, "added": sorted(app_ids), "removed": []}
            data.append([f"user-collections.{cid}", {
                "key": f"user-collections.{cid}",
                "timestamp": int(datetime.now().timestamp()),
                "value": json.dumps(val_obj),
                "version": str(next_version),
                "conflictResolutionMethod": "custom",
                "strMethodId": "union-collections",
            }])
            created.append(display)
        next_version += 1

    with open(cloud_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))

    return {"assigned": assigned, "backup": backup_path.name,
            "created": created, "updated": updated}


def genre_suggestion(app_id, http=requests):
    try:
        url = (
            "https://store.steampowered.com/api/appdetails"
            f"?appids={app_id}&filters=genres,categories"
        )
        r = http.get(url, timeout=10)
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
