from __future__ import annotations

from .auto_apply import AutoApplyRunner
from .bot_service import BotService
from .config import Settings, load_settings
from .hh_apply_runner import HhApplyRunner
from .hh_browser_apply import HhBrowserApplyConfig, HhBrowserApplyRunner
from .hh_browser import HhBrowserConfig, HhBrowserRunner
from .hh_resume_runner import HhResumeRunner
from .models import UserSettings
from .hh_search_runner import HhSearchRunner
from .oauth import HhOAuthConfig
from .oauth_web import create_oauth_app
from .storage import SQLiteStore
from .telegram_bot import run_polling_sync


def build_service(settings: Settings) -> BotService:
    store = SQLiteStore(settings.database_path)
    store.initialize()
    resume_id = store.get_selected_resume_id() or settings.default_resume_id
    stored_min_score = store.get_min_score()
    min_score = stored_min_score if stored_min_score is not None else settings.default_min_score
    cover_letter = store.get_cover_letter() or settings.default_cover_letter
    search_text = store.get_search_text() or settings.hh_search_text
    include_keywords = store.get_include_keywords() or settings.include_keywords
    exclude_keywords = store.get_exclude_keywords() or settings.exclude_keywords
    user_settings = UserSettings(
        resume_id=resume_id,
        cover_letter=cover_letter,
        include_keywords=include_keywords,
        exclude_keywords=exclude_keywords,
        min_score=min_score,
    )
    return BotService(
        store=store,
        settings=user_settings,
        oauth_start_url=settings.oauth_start_url,
        oauth_state=settings.oauth_state,
        search_text=search_text,
        search_area=settings.hh_search_area,
    )


def build_oauth_app(settings: Settings):
    store = SQLiteStore(settings.database_path)
    store.initialize()
    return create_oauth_app(
        store=store,
        oauth_config=HhOAuthConfig(
            client_id=settings.hh_client_id,
            client_secret=settings.hh_client_secret,
            redirect_uri=settings.hh_redirect_uri,
            user_agent=settings.hh_user_agent,
        ),
    )


def build_search_runner(settings: Settings, store: SQLiteStore) -> HhSearchRunner:
    return HhSearchRunner(
        store=store,
        oauth_state=settings.oauth_state,
        user_agent=settings.hh_user_agent,
        search_text=settings.hh_search_text,
        area=settings.hh_search_area,
        per_page=settings.hh_search_per_page,
    )


def build_resume_runner(settings: Settings, store: SQLiteStore) -> HhResumeRunner:
    return HhResumeRunner(
        store=store,
        oauth_state=settings.oauth_state,
        user_agent=settings.hh_user_agent,
    )


def build_apply_runner(settings: Settings, store: SQLiteStore) -> HhApplyRunner:
    browser_apply_runner = HhBrowserApplyRunner(
        HhBrowserApplyConfig(
            user_data_dir=settings.browser_user_data_dir,
            headless=settings.browser_headless,
        )
    )
    return HhApplyRunner(
        store=store,
        oauth_state=settings.oauth_state,
        user_agent=settings.hh_user_agent,
        real_apply_enabled=settings.enable_real_apply,
        apply_transport=settings.hh_apply_transport,
        browser_apply_runner=browser_apply_runner,
    )


def build_browser_runner(settings: Settings) -> HhBrowserRunner | None:
    if not settings.enable_browser_search:
        return None
    return HhBrowserRunner(
        HhBrowserConfig(
            search_text=settings.hh_search_text,
            area=settings.hh_search_area,
            limit=settings.browser_search_limit,
            headless=settings.browser_headless,
            user_data_dir=settings.browser_user_data_dir,
        )
    )


def build_auto_apply_runner(settings: Settings, store: SQLiteStore, apply_runner: HhApplyRunner) -> AutoApplyRunner:
    return AutoApplyRunner(
        store=store,
        apply_runner=apply_runner,
        daily_limit=settings.auto_apply_daily_limit,
        delay_seconds=settings.auto_apply_delay_seconds,
        remote_only=settings.auto_apply_remote_only,
        transport_label=settings.hh_apply_transport,
    )


def main() -> None:
    settings = load_settings()
    if settings.run_oauth_server:
        import uvicorn

        uvicorn.run(build_oauth_app(settings), host="0.0.0.0", port=8000)
        return

    service = build_service(settings)
    if settings.run_telegram_polling:
        search_runner = build_search_runner(settings, service.store)
        resume_runner = build_resume_runner(settings, service.store)
        apply_runner = build_apply_runner(settings, service.store)
        auto_apply_runner = build_auto_apply_runner(settings, service.store, apply_runner)
        browser_runner = build_browser_runner(settings)
        run_polling_sync(
            service,
            settings.telegram_bot_token,
            search_runner=search_runner,
            resume_runner=resume_runner,
            apply_runner=apply_runner,
            browser_runner=browser_runner,
            auto_apply_runner=auto_apply_runner,
        )
        return

    print("HH Telegram Bot dry-run foundation ready.")
    print(f"Database: {settings.database_path}")
    print(f"Default minimum score: {settings.default_min_score}")
    print("Set RUN_TELEGRAM_POLLING=1 to start Telegram polling.")


if __name__ == "__main__":
    main()
