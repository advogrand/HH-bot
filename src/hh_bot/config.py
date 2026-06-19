from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    hh_client_id: str
    hh_client_secret: str
    hh_redirect_uri: str
    hh_user_agent: str
    database_path: str
    default_min_score: int
    run_telegram_polling: bool
    default_resume_id: str
    default_cover_letter: str
    include_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...]
    oauth_start_url: str
    oauth_state: str
    run_oauth_server: bool
    hh_search_text: str
    hh_search_area: str | None
    hh_search_per_page: int


def load_settings() -> Settings:
    env = load_dotenv_file(Path(".env"), existing=os.environ)
    return Settings(
        telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN", ""),
        hh_client_id=env.get("HH_CLIENT_ID", ""),
        hh_client_secret=env.get("HH_CLIENT_SECRET", ""),
        hh_redirect_uri=env.get(
            "HH_REDIRECT_URI",
            "http://localhost:8000/oauth/hh/callback",
        ),
        hh_user_agent=env.get("HH_USER_AGENT", "HHBot/0.1 (you@example.com)"),
        database_path=env.get("DATABASE_PATH", "hh_bot.sqlite3"),
        default_min_score=int(env.get("DEFAULT_MIN_SCORE", "60")),
        run_telegram_polling=_bool_env(env, "RUN_TELEGRAM_POLLING"),
        default_resume_id=env.get("DEFAULT_RESUME_ID", "local-dry-run-resume"),
        default_cover_letter=env.get("DEFAULT_COVER_LETTER", ""),
        include_keywords=_csv_env(env, "INCLUDE_KEYWORDS"),
        exclude_keywords=_csv_env(env, "EXCLUDE_KEYWORDS"),
        oauth_start_url=env.get("OAUTH_START_URL", "http://localhost:8000/oauth/hh/start"),
        oauth_state=env.get("OAUTH_STATE", "local-telegram-user"),
        run_oauth_server=_bool_env(env, "RUN_OAUTH_SERVER"),
        hh_search_text=env.get("HH_SEARCH_TEXT", "python"),
        hh_search_area=env.get("HH_SEARCH_AREA") or None,
        hh_search_per_page=int(env.get("HH_SEARCH_PER_PAGE", "20")),
    )


def load_dotenv_file(
    path: str | Path,
    *,
    existing: Mapping[str, str] | None = None,
) -> dict[str, str]:
    values = dict(existing or {})
    env_path = Path(path)
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key in values:
            continue
        values[key] = _strip_quotes(raw_value.strip())
    return values


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _bool_env(env: Mapping[str, str], name: str) -> bool:
    return env.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(env: Mapping[str, str], name: str) -> tuple[str, ...]:
    raw = env.get(name, "")
    return tuple(part.strip() for part in raw.split(",") if part.strip())
