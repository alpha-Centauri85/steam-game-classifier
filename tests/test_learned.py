import json
from pathlib import Path
import steam_core as core


def test_load_missing_file_returns_empty(tmp_path):
    assert core.load_learned(tmp_path / "nope.json") == {}


def test_save_then_load_roundtrip(tmp_path):
    p = tmp_path / "categories.json"
    core.save_learned(p, "Balatro", "MOBA")
    assert core.load_learned(p) == {"balatro": "MOBA"}


def test_save_normalises_name_key(tmp_path):
    p = tmp_path / "categories.json"
    core.save_learned(p, "  Vampire Survivors  ", "ACTION ROGUELITE")
    assert "vampire survivors" in core.load_learned(p)


def test_load_malformed_file_returns_empty(tmp_path):
    p = tmp_path / "categories.json"
    p.write_text("{ this is not json", encoding="utf-8")
    assert core.load_learned(p) == {}
