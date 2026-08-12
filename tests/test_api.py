import pytest
import steam_core as core


class FakeResp:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload


class FakeHttp:
    def __init__(self, payload):
        self._payload = payload
        self.last_url = None
    def get(self, url, timeout=None):
        self.last_url = url
        return FakeResp(self._payload)


def test_get_owned_games_maps_appid_to_name():
    http = FakeHttp({"response": {"games": [
        {"appid": 220, "name": "Half-Life 2"},
        {"appid": 620, "name": "Portal 2"},
    ]}})
    assert core.get_owned_games("KEY", "76561", http=http) == {220: "Half-Life 2", 620: "Portal 2"}


def test_resolve_profiles_url_extracts_id_without_api_call():
    http = FakeHttp({})  # should not be needed
    got = core.resolve_steam_id("KEY", "https://steamcommunity.com/profiles/76561198012345678", http=http)
    assert got == "76561198012345678"
    assert http.last_url is None  # no API call made


def test_resolve_vanity_name_calls_api():
    http = FakeHttp({"response": {"success": 1, "steamid": "76561198012345678"}})
    got = core.resolve_steam_id("KEY", "gabelogannewell", http=http)
    assert got == "76561198012345678"


def test_resolve_unknown_vanity_raises():
    http = FakeHttp({"response": {"success": 42}})
    with pytest.raises(ValueError):
        core.resolve_steam_id("KEY", "no-such-user-9999", http=http)
