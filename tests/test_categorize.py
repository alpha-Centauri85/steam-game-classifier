import steam_core as core


def test_exact_match_from_builtin_map():
    assert core.categorize("Warframe") == "ARPG"


def test_match_is_case_and_whitespace_insensitive():
    assert core.categorize("  WARFRAME  ") == "ARPG"


def test_custom_overrides_builtin():
    assert core.categorize("Warframe", {"warframe": "FPS"}) == "FPS"


def test_year_suffix_is_stripped():
    # "tomb raider (2013)" should match the same as "tomb raider"
    custom = {"tomb raider": "ACTION/ADVENTURE"}
    assert core.categorize("Tomb Raider (2013)", custom) == "ACTION/ADVENTURE"


def test_unknown_game_returns_none():
    assert core.categorize("Totally Made Up Game 9999") is None


def test_valid_categories_are_sorted_and_nonempty():
    cats = core.valid_categories()
    assert cats == sorted(cats)
    assert "ARPG" in cats


def test_collection_display_maps_key_to_name():
    assert core.collection_display("MANAGEMENT/TYCOON") == "Management/Tycoon"
