import json
import webbrowser
from pathlib import Path
from threading import Timer
from flask import Flask, jsonify, request, send_from_directory

import steam_core as core

BASE = Path(__file__).parent
STATIC = BASE / "static"
CONFIG_PATH_DEFAULT = BASE / "config.json"


def load_config(path):
    path = Path(path)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(path, cfg):
    Path(path).write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def create_app(config_path=CONFIG_PATH_DEFAULT):
    app = Flask(__name__, static_folder=None)
    app.config["CONFIG_PATH"] = Path(config_path)

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.get("/static/<path:name>")
    def static_files(name):
        return send_from_directory(STATIC, name)

    @app.get("/api/config")
    def get_config():
        cfg = load_config(app.config["CONFIG_PATH"])
        return jsonify({
            "api_key_set": bool(cfg.get("api_key")),
            "steam_id": cfg.get("steam_id", ""),
            "steam_path": cfg.get("steam_path", ""),
        })

    @app.post("/api/config")
    def set_config():
        body = request.get_json(force=True)
        save_config(app.config["CONFIG_PATH"], {
            "api_key": body.get("api_key", ""),
            "steam_id": body.get("steam_id", ""),
            "steam_path": body.get("steam_path", ""),
        })
        return jsonify({"ok": True})

    @app.delete("/api/config")
    def forget_config():
        p = Path(app.config["CONFIG_PATH"])
        if p.exists():
            p.unlink()
        return jsonify({"ok": True})

    @app.get("/api/steam-status")
    def steam_status():
        cfg = load_config(app.config["CONFIG_PATH"])
        path = cfg.get("steam_path") or None
        accounts = core.list_steam_accounts(path)
        return jsonify({
            "running": core.is_steam_running(),
            "cloud_found": bool(accounts),
            "accounts": [a["steam_id3"] for a in accounts],
        })

    @app.get("/api/categories")
    def categories():
        return jsonify({"categories": core.valid_categories()})

    @app.post("/api/resolve-id")
    def resolve_id():
        body = request.get_json(force=True)
        try:
            sid = core.resolve_steam_id(body.get("api_key", ""), body.get("profile", ""))
            return jsonify({"steam_id": sid})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.post("/api/preview")
    def preview():
        body = request.get_json(force=True)
        cfg = load_config(app.config["CONFIG_PATH"])
        path = cfg.get("steam_path") or None
        try:
            cloud = core.find_cloud_json(path)
            with open(cloud, encoding="utf-8") as f:
                data = json.load(f)
            owned = core.get_owned_games(body["api_key"], body["steam_id"])
            learned = core.load_learned(core.CATEGORIES_FILE_DEFAULT)
            cs = core.build_change_set(owned, data, learned, overwrite=body.get("overwrite", False))
            return jsonify(cs)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.post("/api/apply")
    def apply():
        body = request.get_json(force=True)
        if not body.get("acknowledged"):
            return jsonify({"error": "Please acknowledge you have closed Steam on all devices."}), 409
        if core.is_steam_running():
            return jsonify({"error": "Steam is still running on this PC. Close it first."}), 409
        cfg = load_config(app.config["CONFIG_PATH"])
        path = cfg.get("steam_path") or None
        try:
            cloud = core.find_cloud_json(path)
            # Persist any newly-learned categories from resolved unknowns.
            for name, cat in (body.get("learned") or {}).items():
                core.save_learned(core.CATEGORIES_FILE_DEFAULT, name, cat)
            result = core.apply_assignments(cloud, body["assignments"], overwrite=body.get("overwrite", False))
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    return app


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    Timer(1.0, _open_browser).start()
    create_app().run(host="127.0.0.1", port=5000, debug=False)
