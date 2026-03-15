"""Application settings loaded from environment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the watcher."""

    discord_webhook_url: str
    sqlite_db_path: Path
    min_score: int = 60
    max_posts_per_run: int = 20
    log_level: str = "INFO"
    request_timeout_seconds: float = 15.0
    request_delay_seconds: float = 1.0
    user_agent: str = "alternance-discord-watcher/1.0"
    bootstrap_lookback_days: int = 30
    hellowork_max_pages: int = 2
    wttj_max_pages: int = 2


def load_settings() -> Settings:
    """Load settings from .env and process environment."""

    load_dotenv()
    db_path = Path(os.getenv("SQLITE_DB_PATH", "./data/offers.db"))
    return Settings(
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
        sqlite_db_path=db_path,
        min_score=int(os.getenv("MIN_SCORE", "60")),
        max_posts_per_run=int(os.getenv("MAX_POSTS_PER_RUN", "20")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        request_delay_seconds=float(os.getenv("REQUEST_DELAY_SECONDS", "1.0")),
        user_agent=os.getenv("USER_AGENT", "alternance-discord-watcher/1.0"),
        bootstrap_lookback_days=int(os.getenv("BOOTSTRAP_LOOKBACK_DAYS", "30")),
        hellowork_max_pages=int(os.getenv("HELLOWORK_MAX_PAGES", "2")),
        wttj_max_pages=int(os.getenv("WTTJ_MAX_PAGES", "2")),
    )
