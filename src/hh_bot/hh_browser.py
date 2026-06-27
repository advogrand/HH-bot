from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from .models import Vacancy


class HhBrowserError(Exception):
    pass


@dataclass(frozen=True)
class HhBrowserConfig:
    search_text: str
    area: str | None = None
    limit: int = 10
    headless: bool = False
    user_data_dir: str = ".hh-browser-profile"


class HhBrowserRunner:
    def __init__(self, config: HhBrowserConfig) -> None:
        self.search_text = config.search_text
        self.area = config.area
        self.limit = config.limit
        self.headless = config.headless
        self.user_data_dir = config.user_data_dir

    async def fetch_vacancies(self) -> list[Vacancy]:
        return await asyncio.to_thread(
            run_browser_search,
            search_text=self.search_text,
            area=self.area,
            limit=self.limit,
            headless=self.headless,
            user_data_dir=self.user_data_dir,
        )


def run_browser_search(
    *,
    search_text: str,
    area: str | None = None,
    limit: int = 10,
    headless: bool = False,
    user_data_dir: str = ".hh-browser-profile",
) -> list[Vacancy]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise HhBrowserError("Playwright is not installed. Run `python -m pip install -e .`.") from exc

    search_url = _build_search_url(search_text=search_text, area=area)
    profile_dir = Path(user_data_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=headless,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(search_url, wait_until="domcontentloaded")
            try:
                page.wait_for_selector('[data-qa="vacancy-serp__vacancy"]', timeout=60_000)
            except PlaywrightTimeoutError as exc:
                raise HhBrowserError(
                    "hh.ru did not show vacancy cards. Log in manually, solve captcha if shown, then retry."
                ) from exc
            scroll_until_stable(page)
            return collect_vacancies_for_review(page, limit=limit)
        finally:
            context.close()


def collect_vacancies_for_review(page, *, limit: int = 10) -> list[Vacancy]:
    cards = page.locator('[data-qa="vacancy-serp__vacancy"]')
    vacancies: list[Vacancy] = []

    for index in range(cards.count()):
        if len(vacancies) >= limit:
            break
        card = cards.nth(index)
        title_link = card.locator('a[data-qa="serp-item__title"]').first
        href = _safe_attr(title_link, "href")
        vacancy_id = _vacancy_id_from_url(href)
        title = _first_text(
            card,
            [
                '[data-qa="serp-item__title-text"]',
                'a[data-qa="serp-item__title"]',
            ],
        )
        if not vacancy_id or not title:
            continue

        requirement = _first_text(card, ['[data-qa="vacancy-serp__vacancy_snippet_requirement"]'])
        responsibility = _first_text(card, ['[data-qa="vacancy-serp__vacancy_snippet_responsibility"]'])
        full_card_text = _safe_inner_text(card)
        relations = ()
        if card.locator('[data-qa="vacancy-serp__vacancy_response"]').count():
            relations = ("browser_apply_available",)

        vacancies.append(
            Vacancy(
                id=vacancy_id,
                name=title,
                employer_name=_first_text(card, ['[data-qa="vacancy-serp__vacancy-employer-text"]']),
                url=href or f"https://hh.ru/vacancy/{vacancy_id}",
                description=" ".join(
                    part for part in [requirement, responsibility, full_card_text] if part
                ),
                area=_first_text(card, ['[data-qa="vacancy-serp__vacancy-address"]']) or None,
                relations=relations,
            )
        )

    return vacancies


def scroll_until_stable(
    page,
    *,
    pause_ms: int = 900,
    max_scrolls: int = 12,
    stable_rounds_needed: int = 2,
) -> None:
    cards = page.locator('[data-qa="vacancy-serp__vacancy"]')
    previous_count = cards.count()
    stable_rounds = 0

    for _ in range(max_scrolls):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(pause_ms)
        current_count = cards.count()
        if current_count > previous_count:
            previous_count = current_count
            stable_rounds = 0
            continue
        stable_rounds += 1
        if stable_rounds >= stable_rounds_needed:
            return


def _build_search_url(*, search_text: str, area: str | None) -> str:
    params = {"text": search_text}
    if area:
        params["area"] = area
    return f"https://hh.ru/search/vacancy?{urlencode(params)}"


def _first_text(card, selectors: list[str]) -> str:
    for selector in selectors:
        locator = card.locator(selector).first
        if locator.count():
            return locator.inner_text().strip()
    return ""


def _safe_attr(locator, name: str) -> str:
    if not locator.count():
        return ""
    return (locator.get_attribute(name) or "").strip()


def _safe_inner_text(locator) -> str:
    try:
        return locator.inner_text().strip()
    except Exception:
        return ""


def _vacancy_id_from_url(url: str) -> str:
    match = re.search(r"/vacancy/(\d+)", url)
    if match:
        return match.group(1)
    return ""
