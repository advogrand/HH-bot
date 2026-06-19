from __future__ import annotations

import asyncio
from typing import Any

from .bot_service import BotService
from .hh_browser import HhBrowserError
from .hh_vacancies import HhVacancySearchError
from .scoring import evaluate_vacancy


class TelegramCommandAdapter:
    def __init__(
        self,
        service: BotService,
        search_runner: Any | None = None,
        resume_runner: Any | None = None,
        apply_runner: Any | None = None,
        browser_runner: Any | None = None,
    ) -> None:
        self.service = service
        self.search_runner = search_runner
        self.resume_runner = resume_runner
        self.apply_runner = apply_runner
        self.browser_runner = browser_runner

    async def handle_message(self, message: Any) -> None:
        text = getattr(message, "text", None) or ""
        command, _, arg = text.strip().partition(" ")
        if command == "/search" and self.search_runner is not None:
            if hasattr(self.search_runner, "search_text"):
                self.search_runner.search_text = self.service.search_text
            try:
                vacancies = await self.search_runner.fetch_vacancies()
            except HhVacancySearchError as exc:
                await message.answer(str(exc))
                return
            if not vacancies:
                await message.answer("No vacancies found. Check /settings and try another /set_search query.")
                return
            self.service.vacancies = vacancies
        if command == "/resumes" and self.resume_runner is not None:
            resumes = await self.resume_runner.fetch_resumes()
            if not resumes:
                await message.answer("Connect hh.ru first with /connect, then run /resumes again.")
                return
            self.service.resumes = resumes
        if command == "/browser_search":
            if self.browser_runner is None:
                await message.answer("Browser-assisted search is not configured.")
                return
            if hasattr(self.browser_runner, "search_text"):
                self.browser_runner.search_text = arg.strip() or self.service.search_text
            try:
                vacancies = await self.browser_runner.fetch_vacancies()
            except HhBrowserError as exc:
                await message.answer(str(exc))
                return
            if not vacancies:
                await message.answer("No visible hh.ru vacancy cards found in browser.")
                return
            self.service.vacancies = vacancies
            await message.answer(self.service.handle_command("/search"))
            return
        if command == "/approve" and self.apply_runner is not None:
            vacancy = self.service._find_vacancy(arg.strip())
            if vacancy is None:
                await message.answer(f"Vacancy {arg.strip() or '<empty>'} not found in current queue.")
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
                await message.answer(f"Vacancy {vacancy.id} already has a recorded response.")
                return
            result = await self.apply_runner.approve(
                vacancy=vacancy,
                settings=self.service.settings,
                score=score,
            )
            await message.answer(result.user_message)
            return
        response = self.service.handle_command(text)
        await message.answer(response)


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
            "settings",
            "set_search",
            "set_score",
            "set_resume",
            "set_letter",
            "search",
            "browser_search",
            "approve",
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
    )
    await dispatcher.start_polling(bot)


def run_polling_sync(
    service: BotService,
    token: str,
    search_runner: Any | None = None,
    resume_runner: Any | None = None,
    apply_runner: Any | None = None,
    browser_runner: Any | None = None,
) -> None:
    asyncio.run(
        run_polling(
            service,
            token,
            search_runner=search_runner,
            resume_runner=resume_runner,
            apply_runner=apply_runner,
            browser_runner=browser_runner,
        )
    )


class _message_with_text:
    def __init__(self, message: Any, text: str) -> None:
        self._message = message
        self.text = text

    async def answer(self, text: str) -> None:
        await self._message.answer(text)
