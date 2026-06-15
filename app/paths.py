import os
from pathlib import Path


def app_root() -> Path:
    env = os.environ.get("JOBMIND_APP_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def static_dir() -> Path:
    return app_root() / "app" / "static"


def templates_dir() -> Path:
    return app_root() / "app" / "templates"
