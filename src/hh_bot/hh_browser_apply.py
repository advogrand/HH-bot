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
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
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
            except PlaywrightTimeoutError:
                return _failed("browser_error", "timeout", "hh.ru page load timed out.")
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

    return ApplyResult(ok=True, status="sent", user_message=f"Browser response attempted for vacancy {vacancy.id}.")


RESPONSE_BUTTON_SELECTORS = (
    '[data-qa="vacancy-response-link-top"]',
    '[data-qa="vacancy-response-link-bottom"]',
    '[data-qa="vacancy-serp__vacancy_response"]',
    'a:has-text("Откликнуться")',
    'button:has-text("Откликнуться")',
)

MESSAGE_FIELD_SELECTORS = (
    '[data-qa="vacancy-response-popup-form-letter-input"]',
    'textarea[name="message"]',
    'textarea',
)

SUBMIT_BUTTON_SELECTORS = (
    '[data-qa="vacancy-response-submit-popup"]',
    'button:has-text("Отправить")',
    'button:has-text("Откликнуться")',
)


STOP_MARKERS = (
    ("captcha_required", ("captcha", "капча", "подтвердите, что вы не робот")),
    ("test_required", ("тестовое задание", "пройти тест", "вакансия с тестом")),
    ("questions_required", ("ответьте на вопросы", "вопросы работодателя", "работодатель просит ответить")),
    ("not_logged_in", ("войдите", "войти в личный кабинет", "авторизация")),
    ("access_restricted", ("доступ ограничен", "слишком много запросов", "подозрительная активность")),
)


def _detect_stop_state(text: str) -> ApplyResult | None:
    for value, markers in STOP_MARKERS:
        if any(marker in text for marker in markers):
            return _failed(value, value, f"Browser apply stopped: {value}.")
    return None


def _looks_sent(text: str) -> bool:
    return any(marker in text for marker in ("отклик отправлен", "вы откликнулись", "резюме отправлено"))


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
