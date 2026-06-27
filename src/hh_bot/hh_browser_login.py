from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HhBrowserLoginConfig:
    user_data_dir: str = ".hh-browser-profile"
    headless: bool = False
    wait_seconds: int = 300


class HhBrowserLoginRunner:
    def __init__(self, config: HhBrowserLoginConfig) -> None:
        self.config = config

    async def open_login(self) -> str:
        return await asyncio.to_thread(run_browser_login, config=self.config)


def run_browser_login(*, config: HhBrowserLoginConfig) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Run `python -m pip install -e .`.") from exc

    profile_dir = Path(config.user_data_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=config.headless,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://hh.ru/", wait_until="domcontentloaded", timeout=60_000)
            deadline_ms = config.wait_seconds * 1_000
            elapsed_ms = 0
            while elapsed_ms < deadline_ms:
                if _looks_logged_in(page):
                    return "hh.ru browser profile is logged in. You can run /browser_search now."
                page.wait_for_timeout(2_000)
                elapsed_ms += 2_000
            return (
                "Login window timeout. If you finished login, try /browser_search. "
                "If not, run /browser_login again."
            )
        finally:
            context.close()


def _looks_logged_in(page) -> bool:
    text = _safe_page_text(page)
    if any(marker in text for marker in LOGIN_MARKERS):
        return False
    return any(marker in text for marker in LOGGED_IN_MARKERS)


LOGIN_MARKERS = (
    "\u0432\u043e\u0439\u0442\u0438",
    "\u0432\u0445\u043e\u0434",
    "\u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f",
)

LOGGED_IN_MARKERS = (
    "\u043c\u043e\u0438 \u0440\u0435\u0437\u044e\u043c\u0435",
    "\u043e\u0442\u043a\u043b\u0438\u043a\u0438",
    "\u043f\u0440\u043e\u0444\u0438\u043b\u044c",
)


def _safe_page_text(page) -> str:
    try:
        return page.locator("body").inner_text().strip().lower()
    except Exception:
        return ""
