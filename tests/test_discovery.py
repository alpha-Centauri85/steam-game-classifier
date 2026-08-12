import json
import pytest
import steam_core as core


def _make_steam(tmp_path, id3):
    cloud = tmp_path / "userdata" / id3 / "config" / "cloudstorage"
    cloud.mkdir(parents=True)
    (cloud / "cloud-storage-namespace-1.json").write_text("[]", encoding="utf-8")
    return tmp_path


def test_lists_single_account(tmp_path):
    _make_steam(tmp_path, "12345")
    accounts = core.list_steam_accounts(tmp_path)
    assert len(accounts) == 1
    assert accounts[0]["steam_id3"] == "12345"


def test_find_cloud_json_single_account(tmp_path):
    _make_steam(tmp_path, "12345")
    p = core.find_cloud_json(tmp_path)
    assert p.name == "cloud-storage-namespace-1.json"


def test_find_cloud_json_none_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        core.find_cloud_json(tmp_path)


def test_find_cloud_json_multiple_needs_account(tmp_path):
    _make_steam(tmp_path, "111")
    _make_steam(tmp_path, "222")
    with pytest.raises(core.AmbiguousAccountError):
        core.find_cloud_json(tmp_path)
    # but succeeds when told which one
    p = core.find_cloud_json(tmp_path, account_id3="222")
    assert "222" in str(p)
