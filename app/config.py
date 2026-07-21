from pydantic import BaseModel
from dotenv import load_dotenv
import os

from app.paths import app_root, static_dir

load_dotenv()


def _read_app_version() -> str:
    override = os.getenv("APP_VERSION", "").strip()
    if override:
        return override
    try:
        return (app_root() / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def _dev_asset_version() -> str:
    """Local dev has no CI commit SHA to cache-bust static assets with, so the
    ?v= query string used to fall back to a hardcoded literal — meaning every
    CSS/JS edit kept being served from the browser's cache under that exact
    same URL forever, with no way to see the change short of a hard refresh.
    Use the static folder's newest file mtime instead, so the URL actually
    changes whenever a static file is edited."""
    try:
        newest = max(
            (f.stat().st_mtime for f in static_dir().rglob("*") if f.is_file()),
            default=0,
        )
        return str(int(newest))
    except OSError:
        return "premium-v9"


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "JobMind Match")
    app_env: str = os.getenv("APP_ENV", "dev")
    app_version: str = _read_app_version()
    update_repo: str = os.getenv("UPDATE_REPO", "farazgoal-boop/jobmind-match")
    asset_version: str = (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("GITHUB_SHA")
        or os.getenv("APP_ASSET_VERSION")
        or _dev_asset_version()
    )[:12]
    database_url: str = os.getenv(
        "DATABASE_URL",
        (
            f"sqlite:///{os.getenv('JOBMIND_DATA_DIR', '.')}/jobmind.db"
            if os.getenv("APP_ENV") == "android"
            else "sqlite:///./jobmind.db"
        ),
    )
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_pass: str = os.getenv("SMTP_PASS", "")
    daily_digest_hour: int = int(os.getenv("DAILY_DIGEST_HOUR", "9"))
    daily_digest_top_k: int = int(os.getenv("DAILY_DIGEST_TOP_K", "5"))
    free_monthly_match_limit: int = int(os.getenv("FREE_MONTHLY_MATCH_LIMIT", "50"))
    free_sources: str = os.getenv("FREE_SOURCES", "remotive,weworkremotely")
    premium_sources: str = os.getenv("PREMIUM_SOURCES", "remotive,weworkremotely,arbeitnow")


settings = Settings()
