from __future__ import annotations

import asyncio
from typing import Any

from .bot_service import BotService


class TelegramCommandAdapter:
    def __init__(
        self,
        service: BotService,
        search_runner: Any | None = None,
        resume_runner: Any | None = None,
    ) -> None:
        self.service = service
        self.search_runner = search_runner
        self.resume_runner = resume_runner

    async def handle_message(self, message: Any) -> None:
        text = getattr(message, "text", None) or ""
        command = text.strip().partition(" ")[0]
        if command == "/search" and self.search_runner is not None:
            vacancies = await self.search_runner.fetch_vacancies()
            if not vacancies:
                await message.answer("Connect hh.ru first with /connect, then run /search again.")
                return
            self.service.vacancies = vacancies
        if command == "/resumes" and self.resume_runner is not None:
            resumes = await self.resume_runner.fetch_resumes()
            if not resumes:
                await message.answer("Connect hh.ru first with /connect, then run /resumes again.")
                return
            self.service.resumes = resumes
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
            "search",
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
    )
    await dispatcher.start_polling(bot)


def run_polling_sync(
    service: BotService,
    token: str,
    search_runner: Any | None = None,
    resume_runner: Any | None = None,
) -> None:
    asyncio.run(
        run_polling(
            service,
            token,
            search_runner=search_runner,
            resume_runner=resume_runner,
        )
    )


class _message_with_text:
    def __init__(self, message: Any, text: str) -> None:
        self._message = message
        self.text = text

    async def answer(self, text: str) -> None:
        await self._message.answer(text)
