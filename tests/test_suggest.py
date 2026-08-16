import steam_core as core


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeHttp:
    def __init__(self, tags_by_id):
        self.tags_by_id = tags_by_id
        self.calls = []

    def get(self, url, params=None, timeout=None):
        app_id = int(params["appid"])
        self.calls.append(app_id)
        return FakeResponse({"tags": self.tags_by_id.get(app_id, {})})


# --- franchise matching --------------------------------------------------

def test_franchise_match_catches_sequel():
    match = core.franchise_match("Orcs Must Die! 3")
    assert match["category"] == "TOWER DEFENCE"


def test_franchise_match_ignores_titles_that_are_too_short():
    # "ink" is a real entry in the map but far too generic to match on.
    assert core.franchise_match("Inkbound") is None


def test_franchise_match_requires_a_word_boundary():
    assert core.franchise_match("Portalis") is None


def test_franchise_match_uses_learned_categories():
    learned = {"my custom game": "FPS"}
    match = core.franchise_match("My Custom Game 2", learned)
    assert match["category"] == "FPS"


# --- tag mapping ---------------------------------------------------------

def test_specific_tag_beats_generic_ones():
    # Kingdom Hearts: JRPG must win over Action/RPG/Adventure.
    hits = core.categories_from_tags(["Action", "RPG", "Adventure", "JRPG"])
    assert hits[0][0] == "JRPG"


def test_tower_defense_beats_coop_and_action():
    # Orcs Must Die! 3: the exact case Valve's genre list gets wrong.
    hits = core.categories_from_tags(
        ["Tower Defense", "Co-op", "Strategy", "Third-Person Shooter", "Action"]
    )
    assert hits[0][0] == "TOWER DEFENCE"


def test_categories_from_tags_is_empty_without_matches():
    assert core.categories_from_tags(["Great Soundtrack", "Emotional"]) == []


# --- suggestions ---------------------------------------------------------

def test_franchise_match_outranks_tags():
    suggestion = core.suggest_category(
        1522820, "Orcs Must Die! 3", None, ["Action", "Co-op"]
    )
    assert suggestion["category"] == "TOWER DEFENCE"
    assert suggestion["confidence"] == "high"


def test_suggestion_falls_back_to_tags():
    suggestion = core.suggest_category(
        2552430, "KINGDOM HEARTS -HD 1.5+2.5 ReMIX-", None,
        ["Action", "RPG", "Adventure", "JRPG"],
    )
    assert suggestion["category"] == "JRPG"
    assert suggestion["confidence"] == "medium"
    # The reason must name the tag that actually drove the decision.
    assert "JRPG" in suggestion["reason"]


def test_suggestion_reports_no_signal():
    suggestion = core.suggest_category(1, "Something Nobody Has Tagged", None, [])
    assert suggestion["category"] is None
    assert suggestion["confidence"] == "none"


def test_competing_tags_are_surfaced_as_context():
    suggestion = core.suggest_category(
        1522820, "Orcs Must Die! 3", None,
        ["Tower Defense", "Co-op", "Third-Person Shooter"],
    )
    # Even with the category settled, the conflicting reading stays visible.
    assert "Third-Person Shooter" in suggestion["tags"]


# --- network behaviour ---------------------------------------------------

def test_fetch_tags_survives_network_failure():
    class Broken:
        def get(self, *a, **k):
            raise RuntimeError("no network")

    assert core.fetch_steam_tags(123, Broken()) == []


def test_fetch_tags_orders_by_popularity():
    http = FakeHttp({7: {"Action": 10, "Tower Defense": 99}})
    assert core.fetch_steam_tags(7, http)[0] == "Tower Defense"


def test_suggest_categories_batches_both_games():
    http = FakeHttp({
        1522820: {"Tower Defense": 100, "Co-op": 80, "Third-Person Shooter": 40},
        2552430: {"Action": 100, "RPG": 95, "JRPG": 80},
    })
    out = core.suggest_categories(
        [
            {"app_id": 1522820, "name": "Orcs Must Die! 3"},
            {"app_id": 2552430, "name": "KINGDOM HEARTS -HD 1.5+2.5 ReMIX-"},
        ],
        None,
        http,
    )
    assert [s["category"] for s in out] == ["TOWER DEFENCE", "JRPG"]
    # Tags are fetched even for the franchise match, so its context survives.
    assert sorted(http.calls) == [1522820, 2552430]


def test_suggest_categories_respects_lookup_cap():
    http = FakeHttp({})
    core.suggest_categories(
        [{"app_id": i, "name": f"Game {i}"} for i in range(10)],
        None, http, max_lookups=3,
    )
    assert len(http.calls) == 3
