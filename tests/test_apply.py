import json
import steam_core as core


def _write_cloud(tmp_path, entries):
    p = tmp_path / "cloud-storage-namespace-1.json"
    p.write_text(json.dumps(entries), encoding="utf-8")
    return p


def _collection_entry(name, cid, added):
    val = {"id": cid, "name": name, "added": added, "removed": []}
    return [f"user-collections.{cid}", {
        "key": f"user-collections.{cid}", "value": json.dumps(val),
        "version": "5", "timestamp": 1,
    }]


def test_apply_creates_new_collection(tmp_path):
    p = _write_cloud(tmp_path, [])
    result = core.apply_assignments(p, {"ARPG": [220]})
    assert result["assigned"] == 1
    data = json.loads(p.read_text(encoding="utf-8"))
    colls, _, _ = core.load_collections(data)
    assert 220 in colls["ARPG"]["added"]


def test_apply_makes_a_backup(tmp_path):
    p = _write_cloud(tmp_path, [])
    result = core.apply_assignments(p, {"ARPG": [220]})
    backup_path = tmp_path / result["backup"]
    assert backup_path.exists()


def test_apply_appends_to_existing_collection(tmp_path):
    p = _write_cloud(tmp_path, [_collection_entry("ARPG", "aa", [111])])
    core.apply_assignments(p, {"ARPG": [222]})
    data = json.loads(p.read_text(encoding="utf-8"))
    colls, _, _ = core.load_collections(data)
    assert set(colls["ARPG"]["added"]) == {111, 222}


def test_overwrite_removes_from_old_managed_collection(tmp_path):
    p = _write_cloud(tmp_path, [_collection_entry("FPS", "ff", [220])])
    core.apply_assignments(p, {"ARPG": [220]}, overwrite=True)
    data = json.loads(p.read_text(encoding="utf-8"))
    colls, _, _ = core.load_collections(data)
    assert 220 not in colls["FPS"]["added"]
    assert 220 in colls["ARPG"]["added"]
