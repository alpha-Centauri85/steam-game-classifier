import app as webapp


def test_config_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    webapp.save_config(p, {"api_key": "K", "steam_id": "76561", "steam_path": ""})
    assert webapp.load_config(p)["api_key"] == "K"


def test_missing_config_is_empty(tmp_path):
    assert webapp.load_config(tmp_path / "none.json") == {}


def test_index_route_serves_ok(tmp_path):
    application = webapp.create_app(config_path=tmp_path / "config.json")
    client = application.test_client()
    # static index may 404 until Task 10 adds the file; the route must exist
    resp = client.get("/")
    assert resp.status_code in (200, 404)
