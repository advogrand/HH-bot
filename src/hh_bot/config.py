from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    hh_client_id: str
    hh_client_secret: str
    hh_redirect_uri: str
    hh_user_agent: str
    database_path: str
    default_min_score: int


def load_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        hh_client_id=os.getenv("HH_CLIENT_ID", ""),
        hh_client_secret=os.getenv("HH_CLIENT_SECRET", ""),
        hh_redirect_uri=os.getenv(
            "HH_REDIRECT_URI",
            "http://localhost:8000/oauth/hh/callback",
        ),
        hh_user_agent=os.getenv("HH_USER_AGENT", "HHBot/0.1 (you@example.com)"),
        database_path=os.getenv("DATABASE_PATH", "hh_bot.sqlite3"),
        default_min_score=int(os.getenv("DEFAULT_MIN_SCORE", "60")),
    )
