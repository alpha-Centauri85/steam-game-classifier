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

    return app


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    Timer(1.0, _open_browser).start()
    create_app().run(host="127.0.0.1", port=5000, debug=False)
