import tempfile
import unittest
from pathlib import Path

from hh_bot.bot_service import BotService
from hh_bot.hh_apply import ApplyResult
from hh_bot.hh_resumes import HhResumeError
from hh_bot.hh_vacancies import HhVacancySearchError
from hh_bot.models import Resume, UserSettings, Vacancy
from hh_bot.storage import SQLiteStore
from hh_bot.telegram_bot import TelegramCommandAdapter, ensure_bot_token, split_telegram_text


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

    async def test_adapter_explains_hh_resume_api_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-direct", "Hello"))
            adapter = TelegramCommandAdapter(service, resume_runner=ErrorResumeRunner())
            message = FakeMessage("/resumes")

            await adapter.handle_message(message)

            self.assertIn("hh.ru denied resume list access", message.answers[0])
            self.assertIn("resume-direct", message.answers[0])

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
            self.assertIn("Searching hh.ru in browser", message.answers[0])
            self.assertIn("Python Developer", message.answers[-1])

    async def test_adapter_opens_browser_login(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))
            browser_login_runner = FakeBrowserLoginRunner()
            adapter = TelegramCommandAdapter(service, browser_login_runner=browser_login_runner)
            message = FakeMessage("/browser_login")

            await adapter.handle_message(message)

            self.assertTrue(browser_login_runner.was_called)
            self.assertIn("Opening the bot browser profile", message.answers[0])
            self.assertIn("logged in", message.answers[1])

    async def test_adapter_splits_long_browser_search_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("designer",),
                    min_score=55,
                ),
                search_text="designer",
            )
            browser_runner = ManyVacanciesBrowserRunner()
            adapter = TelegramCommandAdapter(service, browser_runner=browser_runner)
            message = FakeMessage("/browser_search")

            await adapter.handle_message(message)

            self.assertGreater(len(message.answers), 2)
            self.assertTrue(all(len(answer) <= 3900 for answer in message.answers))

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

    async def test_adapter_runs_auto_apply_with_confirmation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("дизайнер",),
                    min_score=55,
                ),
                vacancies=[
                    Vacancy(
                        id="vacancy-1",
                        name="Digital Designer",
                        employer_name="Acme",
                        url="https://hh.ru/vacancy/1",
                        description="Удаленная работа дизайнер",
                    )
                ],
            )
            auto_apply_runner = FakeAutoApplyRunner()
            adapter = TelegramCommandAdapter(service, auto_apply_runner=auto_apply_runner)
            message = FakeMessage("/auto_apply confirm")

            await adapter.handle_message(message)

            self.assertTrue(auto_apply_runner.was_called)
            self.assertTrue(auto_apply_runner.confirm)
            self.assertIn("Auto apply started", message.answers[0])
            self.assertIn("Auto apply finished", message.answers[1])


class TelegramConfigTests(unittest.TestCase):
    def test_ensure_bot_token_rejects_missing_token(self):
        with self.assertRaisesRegex(ValueError, "TELEGRAM_BOT_TOKEN"):
            ensure_bot_token("")

    def test_ensure_bot_token_returns_token(self):
        self.assertEqual(ensure_bot_token("123:abc"), "123:abc")

    def test_split_telegram_text_keeps_chunks_under_limit(self):
        text = "\n\n---\n\n".join(f"Vacancy {index}\n" + ("x" * 700) for index in range(10))

        chunks = split_telegram_text(text, limit=1200)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 1200 for chunk in chunks))


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


class ManyVacanciesBrowserRunner:
    def __init__(self) -> None:
        self.search_text = ""

    async def fetch_vacancies(self) -> list[Vacancy]:
        return [
            Vacancy(
                id=str(index),
                name=f"Designer {index}",
                employer_name="Acme",
                url=f"https://hh.ru/vacancy/{index}",
                description="designer " + ("long text " * 80),
                relations=("browser_apply_available",),
            )
            for index in range(80)
        ]


class FakeBrowserLoginRunner:
    def __init__(self) -> None:
        self.was_called = False

    async def open_login(self) -> str:
        self.was_called = True
        return "hh.ru browser profile is logged in."


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


class ErrorResumeRunner:
    async def fetch_resumes(self) -> list[Resume]:
        raise HhResumeError("hh.ru denied resume list access.")


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


class FakeAutoApplyRunner:
    def __init__(self) -> None:
        self.was_called = False
        self.confirm = False

    async def run(self, *, vacancies, settings, confirm):
        self.was_called = True
        self.confirm = confirm
        return type("Summary", (), {"user_message": "Auto apply finished"})()
