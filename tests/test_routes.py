import app as webapp


def _client(tmp_path):
    return webapp.create_app(config_path=tmp_path / "config.json").test_client()


def test_config_post_then_get_masks_key(tmp_path):
    c = _client(tmp_path)
    c.post("/api/config", json={"api_key": "SECRET", "steam_id": "76561", "steam_path": ""})
    body = c.get("/api/config").get_json()
    assert body["api_key_set"] is True
    assert "SECRET" not in str(body)
    assert body["steam_id"] == "76561"


def test_config_post_empty_key_preserves_saved_key(tmp_path):
    c = _client(tmp_path)
    c.post("/api/config", json={"api_key": "SECRET", "steam_id": "76561", "steam_path": ""})
    # Returning session saves again with a blank key (already stored) — must keep it.
    c.post("/api/config", json={"api_key": "", "steam_id": "76561", "steam_path": ""})
    body = c.get("/api/config").get_json()
    assert body["api_key_set"] is True
    assert body["steam_id"] == "76561"


def test_categories_route(tmp_path):
    body = _client(tmp_path).get("/api/categories").get_json()
    assert "ARPG" in body["categories"]


def test_apply_blocked_without_acknowledgement(tmp_path):
    c = _client(tmp_path)
    resp = c.post("/api/apply", json={"assignments": {"ARPG": [220]}, "acknowledged": False})
    assert resp.status_code == 409
    assert "acknowledge" in resp.get_json()["error"].lower()
