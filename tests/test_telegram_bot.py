import tempfile
import unittest
from pathlib import Path

from hh_bot.bot_service import BotService
from hh_bot.models import UserSettings
from hh_bot.storage import SQLiteStore
from hh_bot.telegram_bot import TelegramCommandAdapter, ensure_bot_token


class FakeMessage:
    def __init__(self, text: str | None) -> None:
        self.text = text
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


class TelegramBotTests(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_replies_with_service_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))
            adapter = TelegramCommandAdapter(service)
            message = FakeMessage("/status")

            await adapter.handle_message(message)

            self.assertEqual(len(message.answers), 1)
            self.assertIn("Mode: semi-automatic dry-run", message.answers[0])

    async def test_adapter_handles_empty_message_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))
            adapter = TelegramCommandAdapter(service)
            message = FakeMessage(None)

            await adapter.handle_message(message)

            self.assertEqual(len(message.answers), 1)
            self.assertIn("Unknown command", message.answers[0])


class TelegramConfigTests(unittest.TestCase):
    def test_ensure_bot_token_rejects_missing_token(self):
        with self.assertRaisesRegex(ValueError, "TELEGRAM_BOT_TOKEN"):
            ensure_bot_token("")

    def test_ensure_bot_token_returns_token(self):
        self.assertEqual(ensure_bot_token("123:abc"), "123:abc")


if __name__ == "__main__":
    unittest.main()
