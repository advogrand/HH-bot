from __future__ import annotations

import asyncio
from typing import Any

from .bot_service import BotService


class TelegramCommandAdapter:
    def __init__(self, service: BotService) -> None:
        self.service = service

    async def handle_message(self, message: Any) -> None:
        text = getattr(message, "text", None) or ""
        response = self.service.handle_command(text)
        await message.answer(response)


def ensure_bot_token(token: str) -> str:
    normalized = token.strip()
    if not normalized:
        raise ValueError("TELEGRAM_BOT_TOKEN is required to run Telegram polling.")
    return normalized


def create_dispatcher(service: BotService) -> Any:
    try:
        from aiogram import Dispatcher
        from aiogram.filters import Command, CommandStart
    except ImportError as exc:
        raise RuntimeError(
            "aiogram is not installed. Run `python -m pip install -e .` first."
        ) from exc

    adapter = TelegramCommandAdapter(service)
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def start_handler(message: Any) -> None:
        await adapter.handle_message(_message_with_text(message, "/start"))

    @dispatcher.message(Command("connect", "status", "settings", "search", "approve", "reject", "stop"))
    async def command_handler(message: Any) -> None:
        await adapter.handle_message(message)

    return dispatcher


async def run_polling(service: BotService, token: str) -> None:
    try:
        from aiogram import Bot
    except ImportError as exc:
        raise RuntimeError(
            "aiogram is not installed. Run `python -m pip install -e .` first."
        ) from exc

    bot = Bot(ensure_bot_token(token))
    dispatcher = create_dispatcher(service)
    await dispatcher.start_polling(bot)


def run_polling_sync(service: BotService, token: str) -> None:
    asyncio.run(run_polling(service, token))


class _message_with_text:
    def __init__(self, message: Any, text: str) -> None:
        self._message = message
        self.text = text

    async def answer(self, text: str) -> None:
        await self._message.answer(text)
