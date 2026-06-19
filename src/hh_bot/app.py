from __future__ import annotations

from .bot_service import BotService
from .config import Settings, load_settings
from .models import UserSettings
from .storage import SQLiteStore
from .telegram_bot import run_polling_sync


def build_service(settings: Settings) -> BotService:
    store = SQLiteStore(settings.database_path)
    store.initialize()
    user_settings = UserSettings(
        resume_id=settings.default_resume_id,
        cover_letter=settings.default_cover_letter,
        include_keywords=settings.include_keywords,
        exclude_keywords=settings.exclude_keywords,
        min_score=settings.default_min_score,
    )
    return BotService(store=store, settings=user_settings)


def main() -> None:
    settings = load_settings()
    service = build_service(settings)
    if settings.run_telegram_polling:
        run_polling_sync(service, settings.telegram_bot_token)
        return

    print("HH Telegram Bot dry-run foundation ready.")
    print(f"Database: {settings.database_path}")
    print(f"Default minimum score: {settings.default_min_score}")
    print("Set RUN_TELEGRAM_POLLING=1 to start Telegram polling.")


if __name__ == "__main__":
    main()
