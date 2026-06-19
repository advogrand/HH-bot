import tempfile
import unittest
from pathlib import Path

from hh_bot.bot_service import BotService
from hh_bot.models import UserSettings, Vacancy
from hh_bot.storage import SQLiteStore


class BotServiceTests(unittest.TestCase):
    def test_status_reports_dry_run_and_audit_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))

            message = service.handle_command("/status")

            self.assertIn("Mode: semi-automatic dry-run", message)
            self.assertIn("Audit entries: 0", message)

    def test_search_returns_candidate_message_for_matching_vacancy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("python",),
                    min_score=60,
                ),
                vacancies=[
                    Vacancy(
                        id="1",
                        name="Python Developer",
                        employer_name="Acme",
                        url="https://hh.ru/vacancy/1",
                        description="Python backend",
                    )
                ],
            )

            message = service.handle_command("/search")

            self.assertIn("Python Developer", message)
            self.assertIn("/approve 1", message)

    def test_approve_records_dry_run_audit_entry(self):
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
                        id="1",
                        name="Python Developer",
                        employer_name="Acme",
                        url="https://hh.ru/vacancy/1",
                        description="Python backend",
                    )
                ],
            )

            message = service.handle_command("/approve 1")

            self.assertIn("Dry-run recorded", message)
            self.assertTrue(store.has_response("resume-1", "1"))

    def test_stop_sets_stopped_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))

            message = service.handle_command("/stop")

            self.assertIn("stopped", message.lower())
            self.assertTrue(service.is_stopped)

    def test_connect_returns_oauth_start_link_when_configured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings("resume-1", "Hello"),
                oauth_start_url="http://localhost:8000/oauth/hh/start",
                oauth_state="telegram-user-1",
            )

            message = service.handle_command("/connect")

            self.assertIn("Connect hh.ru", message)
            self.assertIn("http://localhost:8000/oauth/hh/start?state=telegram-user-1", message)


if __name__ == "__main__":
    unittest.main()
