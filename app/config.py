from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "JobMind Match")
    app_env: str = os.getenv("APP_ENV", "dev")
    asset_version: str = (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("GITHUB_SHA")
        or os.getenv("APP_ASSET_VERSION")
        or "premium-v9"
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
