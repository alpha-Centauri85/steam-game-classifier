import json
import steam_core as core


def _collection_entry(name, cid, added):
    val = {"id": cid, "name": name, "added": added, "removed": []}
    return [f"user-collections.{cid}", {
        "key": f"user-collections.{cid}",
        "value": json.dumps(val),
        "version": "5",
        "timestamp": 1,
    }]


def test_uncategorised_known_game_is_a_change():
    data = []  # no collections yet
    owned = {220: "Warframe"}  # Warframe -> ARPG in builtin map
    cs = core.build_change_set(owned, data, learned={}, overwrite=False)
    assert cs["will_change"] == [
        {"app_id": 220, "name": "Warframe", "from": None, "to": "ARPG", "to_display": "ARPG"}
    ]
    assert cs["unknown"] == []
    assert cs["no_change"] == 0


def test_unknown_game_goes_to_unknown():
    owned = {999: "Some Unknown Indie 4242"}
    cs = core.build_change_set(owned, [], learned={}, overwrite=False)
    assert cs["unknown"] == [{"app_id": 999, "name": "Some Unknown Indie 4242"}]
    assert cs["will_change"] == []


def test_already_categorised_skipped_when_not_overwriting():
    # Warframe already in the ARPG collection
    data = [_collection_entry("ARPG", "aa", [220])]
    owned = {220: "Warframe"}
    cs = core.build_change_set(owned, data, learned={}, overwrite=False)
    assert cs["will_change"] == []
    assert cs["no_change"] == 1


def test_overwrite_moves_game_to_correct_collection():
    # Warframe currently mis-filed in FPS; overwrite should propose ARPG
    data = [_collection_entry("FPS", "ff", [220])]
    owned = {220: "Warframe"}
    cs = core.build_change_set(owned, data, learned={}, overwrite=True)
    assert cs["will_change"] == [
        {"app_id": 220, "name": "Warframe", "from": "FPS", "to": "ARPG", "to_display": "ARPG"}
    ]


def test_game_already_in_right_place_is_no_change_under_overwrite():
    data = [_collection_entry("ARPG", "aa", [220])]
    owned = {220: "Warframe"}
    cs = core.build_change_set(owned, data, learned={}, overwrite=True)
    assert cs["will_change"] == []
    assert cs["no_change"] == 1
