from __future__ import annotations

import asyncio
from typing import Any

from .bot_service import BotService
from .hh_browser import HhBrowserError
from .hh_resumes import HhResumeError
from .hh_vacancies import HhVacancySearchError
from .scoring import evaluate_vacancy


TELEGRAM_MESSAGE_LIMIT = 3900


class TelegramCommandAdapter:
    def __init__(
        self,
        service: BotService,
        search_runner: Any | None = None,
        resume_runner: Any | None = None,
        apply_runner: Any | None = None,
        browser_runner: Any | None = None,
        auto_apply_runner: Any | None = None,
    ) -> None:
        self.service = service
        self.search_runner = search_runner
        self.resume_runner = resume_runner
        self.apply_runner = apply_runner
        self.browser_runner = browser_runner
        self.auto_apply_runner = auto_apply_runner

    async def handle_message(self, message: Any) -> None:
        text = getattr(message, "text", None) or ""
        command, _, arg = text.strip().partition(" ")
        if command == "/search" and self.search_runner is not None:
            if hasattr(self.search_runner, "search_text"):
                self.search_runner.search_text = self.service.search_text
            try:
                vacancies = await self.search_runner.fetch_vacancies()
            except HhVacancySearchError as exc:
                await answer_text(message, str(exc))
                return
            if not vacancies:
                await answer_text(message, "No vacancies found. Check /settings and try another /set_search query.")
                return
            self.service.vacancies = vacancies
        if command == "/resumes" and self.resume_runner is not None:
            try:
                resumes = await self.resume_runner.fetch_resumes()
            except HhResumeError as exc:
                await answer_text(message, f"{exc} Current resume: {self.service.settings.resume_id}")
                return
            if not resumes:
                await answer_text(message, "Connect hh.ru first with /connect, then run /resumes again.")
                return
            self.service.resumes = resumes
        if command == "/browser_search":
            if self.browser_runner is None:
                await answer_text(message, "Browser-assisted search is not configured.")
                return
            if hasattr(self.browser_runner, "search_text"):
                self.browser_runner.search_text = arg.strip() or self.service.search_text
            await answer_text(message, "Searching hh.ru in browser. I will send candidates when the page is parsed.")
            try:
                vacancies = await self.browser_runner.fetch_vacancies()
            except HhBrowserError as exc:
                await answer_text(message, str(exc))
                return
            if not vacancies:
                await answer_text(message, "No visible hh.ru vacancy cards found in browser.")
                return
            self.service.vacancies = vacancies
            await answer_text(message, self.service.handle_command("/search"))
            return
        if command == "/approve" and self.apply_runner is not None:
            vacancy = self.service._find_vacancy(arg.strip())
            if vacancy is None:
                await answer_text(message, f"Vacancy {arg.strip() or '<empty>'} not found in current queue.")
                return
            already_applied = self.service.store.has_response(
                self.service.settings.resume_id,
                vacancy.id,
            )
            score = evaluate_vacancy(
                vacancy,
                self.service.settings,
                already_applied=already_applied,
            )
            if already_applied:
                await answer_text(message, f"Vacancy {vacancy.id} already has a recorded response.")
                return
            result = await self.apply_runner.approve(
                vacancy=vacancy,
                settings=self.service.settings,
                score=score,
            )
            await answer_text(message, result.user_message)
            return
        if command == "/auto_apply":
            if self.auto_apply_runner is None:
                await answer_text(message, "Auto apply is not configured.")
                return
            confirm = arg.strip().lower() == "confirm"
            if confirm:
                await answer_text(
                    message,
                    "Auto apply started. I will send a summary when the batch finishes. "
                    "Use /stop if you need to halt future runs."
                )
            summary = await self.auto_apply_runner.run(
                vacancies=self.service.vacancies,
                settings=self.service.settings,
                confirm=confirm,
            )
            await answer_text(message, summary.user_message)
            return
        response = self.service.handle_command(text)
        await answer_text(message, response)


def ensure_bot_token(token: str) -> str:
    normalized = token.strip()
    if not normalized:
        raise ValueError("TELEGRAM_BOT_TOKEN is required to run Telegram polling.")
    return normalized


def create_dispatcher(
    service: BotService,
    search_runner: Any | None = None,
    resume_runner: Any | None = None,
    apply_runner: Any | None = None,
    browser_runner: Any | None = None,
    auto_apply_runner: Any | None = None,
) -> Any:
    try:
        from aiogram import Dispatcher
        from aiogram.filters import Command, CommandStart
    except ImportError as exc:
        raise RuntimeError(
            "aiogram is not installed. Run `python -m pip install -e .` first."
        ) from exc

    adapter = TelegramCommandAdapter(
        service,
        search_runner=search_runner,
        resume_runner=resume_runner,
        apply_runner=apply_runner,
        browser_runner=browser_runner,
        auto_apply_runner=auto_apply_runner,
    )
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start_handler(message: Any) -> None:
        await adapter.handle_message(_message_with_text(message, "/start"))

    @dispatcher.message(
        Command(
            "connect",
            "resumes",
            "use_resume",
            "status",
            "audit",
            "settings",
            "set_search",
            "set_score",
            "set_resume",
            "set_letter",
            "set_include",
            "set_exclude",
            "search",
            "browser_search",
            "approve",
            "auto_apply",
            "reject",
            "stop",
        )
    )
    async def command_handler(message: Any) -> None:
        await adapter.handle_message(message)

    return dispatcher


async def run_polling(
    service: BotService,
    token: str,
    search_runner: Any | None = None,
    resume_runner: Any | None = None,
    apply_runner: Any | None = None,
    browser_runner: Any | None = None,
    auto_apply_runner: Any | None = None,
) -> None:
    try:
        from aiogram import Bot
    except ImportError as exc:
        raise RuntimeError(
            "aiogram is not installed. Run `python -m pip install -e .` first."
        ) from exc

    bot = Bot(ensure_bot_token(token))
    dispatcher = create_dispatcher(
        service,
        search_runner=search_runner,
        resume_runner=resume_runner,
        apply_runner=apply_runner,
        browser_runner=browser_runner,
        auto_apply_runner=auto_apply_runner,
    )
    await dispatcher.start_polling(bot)


def run_polling_sync(
    service: BotService,
    token: str,
    search_runner: Any | None = None,
    resume_runner: Any | None = None,
    apply_runner: Any | None = None,
    browser_runner: Any | None = None,
    auto_apply_runner: Any | None = None,
) -> None:
    asyncio.run(
        run_polling(
            service,
            token,
            search_runner=search_runner,
            resume_runner=resume_runner,
            apply_runner=apply_runner,
            browser_runner=browser_runner,
            auto_apply_runner=auto_apply_runner,
        )
    )


class _message_with_text:
    def __init__(self, message: Any, text: str) -> None:
        self._message = message
        self.text = text

    async def answer(self, text: str) -> None:
        await self._message.answer(text)


async def answer_text(message: Any, text: str) -> None:
    for chunk in split_telegram_text(text):
        await message.answer(chunk)


def split_telegram_text(text: str, *, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    parts, joiner = _split_preferred_parts(text)
    for part in parts:
        separator = joiner if current else ""
        candidate = f"{current}{separator}{part}" if current else part
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(part) <= limit:
            current = part
        else:
            chunks.extend(_split_long_part(part, limit=limit))
    if current:
        chunks.append(current)
    return chunks


def _split_preferred_parts(text: str) -> tuple[list[str], str]:
    if "\n\n---\n\n" in text:
        return text.split("\n\n---\n\n"), "\n\n---\n\n"
    return text.splitlines(), "\n"


def _split_long_part(text: str, *, limit: int) -> list[str]:
    chunks: list[str] = []
    remaining = text
    while remaining:
        chunks.append(remaining[:limit])
        remaining = remaining[limit:]
    return chunks
