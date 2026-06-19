import tempfile
import unittest
from pathlib import Path

from hh_bot.bot_service import BotService
from hh_bot.hh_apply import ApplyResult
from hh_bot.hh_vacancies import HhVacancySearchError
from hh_bot.models import Resume, UserSettings, Vacancy
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

    async def test_adapter_fetches_real_vacancies_before_search_when_runner_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("python",),
                ),
            )
            search_runner = FakeSearchRunner()
            adapter = TelegramCommandAdapter(service, search_runner=search_runner)
            message = FakeMessage("/search")

            await adapter.handle_message(message)

            self.assertTrue(search_runner.was_called)
            self.assertIn("Python Developer", message.answers[0])

    async def test_adapter_uses_updated_search_text_for_real_search(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("python",),
                ),
                search_text="old",
            )
            search_runner = FakeSearchRunner()
            adapter = TelegramCommandAdapter(service, search_runner=search_runner)

            await adapter.handle_message(FakeMessage("/set_search python backend"))
            await adapter.handle_message(FakeMessage("/search"))

            self.assertEqual(search_runner.search_text, "python backend")

    async def test_adapter_explains_empty_search_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("python",),
                ),
            )
            adapter = TelegramCommandAdapter(service, search_runner=EmptySearchRunner())
            message = FakeMessage("/search")

            await adapter.handle_message(message)

            self.assertIn("No vacancies found", message.answers[0])

    async def test_adapter_explains_hh_search_api_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("python",),
                ),
            )
            adapter = TelegramCommandAdapter(service, search_runner=ErrorSearchRunner())
            message = FakeMessage("/search")

            await adapter.handle_message(message)

            self.assertIn("hh.ru API denied vacancy search", message.answers[0])

    async def test_adapter_fetches_resumes_before_resumes_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))
            resume_runner = FakeResumeRunner()
            adapter = TelegramCommandAdapter(service, resume_runner=resume_runner)
            message = FakeMessage("/resumes")

            await adapter.handle_message(message)

            self.assertTrue(resume_runner.was_called)
            self.assertIn("Python Developer", message.answers[0])
            self.assertIn("/use_resume resume-1", message.answers[0])

    async def test_adapter_fetches_browser_vacancies_before_browser_search(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("python",),
                ),
                search_text="python",
            )
            browser_runner = FakeBrowserRunner()
            adapter = TelegramCommandAdapter(service, browser_runner=browser_runner)
            message = FakeMessage("/browser_search")

            await adapter.handle_message(message)

            self.assertTrue(browser_runner.was_called)
            self.assertEqual(browser_runner.search_text, "python")
            self.assertIn("Python Developer", message.answers[-1])

    async def test_adapter_uses_apply_runner_for_approve(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("python",),
                ),
                vacancies=[
                    Vacancy(
                        id="vacancy-1",
                        name="Python Developer",
                        employer_name="Acme",
                        url="https://hh.ru/vacancy/1",
                        description="Python backend",
                    )
                ],
            )
            apply_runner = FakeApplyRunner()
            adapter = TelegramCommandAdapter(service, apply_runner=apply_runner)
            message = FakeMessage("/approve vacancy-1")

            await adapter.handle_message(message)

            self.assertTrue(apply_runner.was_called)
            self.assertIn("Dry-run recorded", message.answers[0])


class TelegramConfigTests(unittest.TestCase):
    def test_ensure_bot_token_rejects_missing_token(self):
        with self.assertRaisesRegex(ValueError, "TELEGRAM_BOT_TOKEN"):
            ensure_bot_token("")

    def test_ensure_bot_token_returns_token(self):
        self.assertEqual(ensure_bot_token("123:abc"), "123:abc")


if __name__ == "__main__":
    unittest.main()


class FakeSearchRunner:
    def __init__(self) -> None:
        self.was_called = False
        self.search_text = ""

    async def fetch_vacancies(self) -> list[Vacancy]:
        self.was_called = True
        return [
            Vacancy(
                id="1",
                name="Python Developer",
                employer_name="Acme",
                url="https://hh.ru/vacancy/1",
                description="Python backend",
            )
        ]


class EmptySearchRunner:
    async def fetch_vacancies(self) -> list[Vacancy]:
        return []


class ErrorSearchRunner:
    async def fetch_vacancies(self) -> list[Vacancy]:
        raise HhVacancySearchError("hh.ru API denied vacancy search. Connect hh.ru with /connect.")


class FakeBrowserRunner:
    def __init__(self) -> None:
        self.was_called = False
        self.search_text = ""

    async def fetch_vacancies(self) -> list[Vacancy]:
        self.was_called = True
        return [
            Vacancy(
                id="browser-1",
                name="Python Developer",
                employer_name="Acme",
                url="https://hh.ru/vacancy/browser-1",
                description="Python backend",
                relations=("browser_apply_available",),
            )
        ]


class FakeResumeRunner:
    def __init__(self) -> None:
        self.was_called = False

    async def fetch_resumes(self) -> list[Resume]:
        self.was_called = True
        return [
            Resume(
                id="resume-1",
                title="Python Developer",
                url="https://api.hh.ru/resumes/resume-1",
            )
        ]


class FakeApplyRunner:
    def __init__(self) -> None:
        self.was_called = False

    async def approve(self, *, vacancy, settings, score):
        self.was_called = True
        return ApplyResult(
            ok=True,
            status="dry_run",
            user_message=f"Dry-run recorded for vacancy {vacancy.id}. No real hh.ru response was sent.",
        )
