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


def data_dir() -> Path:
    """Where this run's SQLite database lives — dev: repo root; desktop:
    ~/.jobmind-match/; android: JOBMIND_DATA_DIR. Deliberately derived from
    settings.database_url rather than a separate config value, so anything
    written here (e.g. the all-time contact export files) always lands next
    to the database it was read from, in every deployment mode, with no new
    setting to keep in sync. Imports app.config locally — app.config itself
    imports this module at load time, so a top-level import would be circular."""
    from app.config import settings

    url = settings.database_url.strip()
    prefix = "sqlite:///"
    if url.lower().startswith(prefix) and not url.lower().startswith(f"{prefix}:memory:"):
        return Path(url[len(prefix):]).expanduser().resolve().parent
    return app_root()
