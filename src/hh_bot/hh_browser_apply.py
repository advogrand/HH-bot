from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from .hh_apply import ApplyResult
from .hh_errors import HhApiError
from .models import UserSettings, Vacancy


class HhBrowserApplyError(Exception):
    pass


@dataclass(frozen=True)
class HhBrowserApplyConfig:
    user_data_dir: str = ".hh-browser-profile"
    headless: bool = False
    timeout_ms: int = 60_000


class HhBrowserApplyRunner:
    def __init__(self, config: HhBrowserApplyConfig) -> None:
        self.config = config

    async def apply(self, *, vacancy: Vacancy, settings: UserSettings) -> ApplyResult:
        return await asyncio.to_thread(
            run_browser_apply,
            vacancy=vacancy,
            settings=settings,
            config=self.config,
        )


def run_browser_apply(
    *,
    vacancy: Vacancy,
    settings: UserSettings,
    config: HhBrowserApplyConfig,
) -> ApplyResult:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise HhBrowserApplyError("Playwright is not installed. Run `python -m pip install -e .`.") from exc

    profile_dir = Path(config.user_data_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=config.headless,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            try:
                page.goto(vacancy.url, wait_until="domcontentloaded", timeout=config.timeout_ms)
            except Exception as exc:
                return _failed(
                    "browser_error",
                    exc.__class__.__name__,
                    f"hh.ru page load failed: {exc.__class__.__name__}.",
                )
            return apply_visible_page(page, vacancy=vacancy, settings=settings)
        finally:
            context.close()


def apply_visible_page(page, *, vacancy: Vacancy, settings: UserSettings) -> ApplyResult:
    stop = _detect_stop_state(_safe_page_text(page))
    if stop is not None:
        return stop

    response_button = _first_visible(page, RESPONSE_BUTTON_SELECTORS)
    if response_button is None:
        return _failed(
            "response_unavailable",
            "response_unavailable",
            "No standard hh.ru response button is visible. Browser apply stopped.",
        )

    response_button.click()
    _wait(page, 700)

    stop = _detect_stop_state(_safe_page_text(page))
    if stop is not None:
        return stop

    cover_letter_button = _first_visible(page, COVER_LETTER_BUTTON_SELECTORS)
    if cover_letter_button is not None:
        cover_letter_button.click()
        _wait(page, 500)

    message_field = _first_visible(page, MESSAGE_FIELD_SELECTORS)
    if message_field is not None and settings.cover_letter:
        message_field.fill(settings.cover_letter)
        _wait(page, 300)

    submit_button = _first_visible(page, SUBMIT_BUTTON_SELECTORS)
    if submit_button is not None:
        submit_button.click()
        _wait(page, 1_000)

    stop = _detect_stop_state(_safe_page_text(page))
    if stop is not None:
        return stop

    if _looks_sent(_safe_page_text(page)):
        return ApplyResult(ok=True, status="sent", user_message=f"Browser response sent for vacancy {vacancy.id}.")

    return _failed(
        "confirmation_missing",
        "confirmation_missing",
        "Browser apply clicked response controls, but hh.ru did not show a sent confirmation.",
    )


RESPONSE_BUTTON_SELECTORS = (
    '[data-qa="vacancy-response-link-top"]',
    '[data-qa="vacancy-response-link-bottom"]',
    '[data-qa="vacancy-serp__vacancy_response"]',
    'a:has-text("\u041e\u0442\u043a\u043b\u0438\u043a\u043d\u0443\u0442\u044c\u0441\u044f")',
    'button:has-text("\u041e\u0442\u043a\u043b\u0438\u043a\u043d\u0443\u0442\u044c\u0441\u044f")',
)

MESSAGE_FIELD_SELECTORS = (
    '[data-qa="vacancy-response-popup-form-letter-input"]',
    'textarea[name="message"]',
    "textarea",
)

COVER_LETTER_BUTTON_SELECTORS = (
    '[data-qa="vacancy-response-letter-toggle"]',
    'button:has-text("\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043f\u0440\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0435")',
    'a:has-text("\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043f\u0440\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0435")',
    'text="\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043f\u0440\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0435"',
)

SUBMIT_BUTTON_SELECTORS = (
    '[data-qa="vacancy-response-submit-popup"]',
    'button:has-text("\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c")',
    'button:has-text("\u041e\u0442\u043a\u043b\u0438\u043a\u043d\u0443\u0442\u044c\u0441\u044f")',
)

STOP_MARKERS = (
    ("captcha_required", ("captcha", "\u043a\u0430\u043f\u0447\u0430", "\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u0435, \u0447\u0442\u043e \u0432\u044b \u043d\u0435 \u0440\u043e\u0431\u043e\u0442")),
    ("test_required", ("\u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0435 \u0437\u0430\u0434\u0430\u043d\u0438\u0435", "\u043f\u0440\u043e\u0439\u0442\u0438 \u0442\u0435\u0441\u0442", "\u0432\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0441 \u0442\u0435\u0441\u0442\u043e\u043c")),
    ("questions_required", ("\u043e\u0442\u0432\u0435\u0442\u044c\u0442\u0435 \u043d\u0430 \u0432\u043e\u043f\u0440\u043e\u0441\u044b", "\u0432\u043e\u043f\u0440\u043e\u0441\u044b \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044f", "\u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044c \u043f\u0440\u043e\u0441\u0438\u0442 \u043e\u0442\u0432\u0435\u0442\u0438\u0442\u044c")),
    ("not_logged_in", ("\u0432\u043e\u0439\u0434\u0438\u0442\u0435", "\u0432\u043e\u0439\u0442\u0438 \u0432 \u043b\u0438\u0447\u043d\u044b\u0439 \u043a\u0430\u0431\u0438\u043d\u0435\u0442", "\u0430\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f")),
    ("access_restricted", ("\u0434\u043e\u0441\u0442\u0443\u043f \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d", "\u0441\u043b\u0438\u0448\u043a\u043e\u043c \u043c\u043d\u043e\u0433\u043e \u0437\u0430\u043f\u0440\u043e\u0441\u043e\u0432", "\u043f\u043e\u0434\u043e\u0437\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u0430\u044f \u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0441\u0442\u044c")),
)


def _detect_stop_state(text: str) -> ApplyResult | None:
    for value, markers in STOP_MARKERS:
        if any(marker in text for marker in markers):
            return _failed(value, value, f"Browser apply stopped: {value}.")
    return None


def _looks_sent(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "\u043e\u0442\u043a\u043b\u0438\u043a \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d",
            "\u0432\u044b \u043e\u0442\u043a\u043b\u0438\u043a\u043d\u0443\u043b\u0438\u0441\u044c",
            "\u0440\u0435\u0437\u044e\u043c\u0435 \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u043e",
        )
    )


def _first_visible(page, selectors: tuple[str, ...]):
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() and locator.is_visible():
                return locator
        except Exception:
            continue
    return None


def _safe_page_text(page) -> str:
    try:
        return page.locator("body").inner_text().strip().lower()
    except Exception:
        return ""


def _wait(page, milliseconds: int) -> None:
    try:
        page.wait_for_timeout(milliseconds)
    except Exception:
        return


def _failed(error_type: str, value: str, message: str) -> ApplyResult:
    error = HhApiError(
        status_code=0,
        type=error_type,
        value=value,
        user_message=message,
    )
    return ApplyResult(ok=False, status="failed", error=error, user_message=message)
