from __future__ import annotations

from .config import load_settings
from .storage import SQLiteStore


def main() -> None:
    settings = load_settings()
    store = SQLiteStore(settings.database_path)
    store.initialize()
    print("HH Telegram Bot dry-run foundation ready.")
    print(f"Database: {settings.database_path}")
    print(f"Default minimum score: {settings.default_min_score}")


if __name__ == "__main__":
    main()
