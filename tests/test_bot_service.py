import tempfile
import unittest
from pathlib import Path

from hh_bot.bot_service import BotService
from hh_bot.models import Resume, UserSettings, Vacancy
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

    def test_resumes_lists_available_resumes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings("resume-1", "Hello"),
                resumes=[
                    Resume(
                        id="resume-1",
                        title="Python Developer",
                        url="https://api.hh.ru/resumes/resume-1",
                    )
                ],
            )

            message = service.handle_command("/resumes")

            self.assertIn("Python Developer", message)
            self.assertIn("/use_resume resume-1", message)

    def test_use_resume_updates_settings_and_persists_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings("old-resume", "Hello"),
                resumes=[
                    Resume(
                        id="resume-1",
                        title="Python Developer",
                        url="https://api.hh.ru/resumes/resume-1",
                    )
                ],
            )

            message = service.handle_command("/use_resume resume-1")

            self.assertIn("Selected resume: Python Developer", message)
            self.assertEqual(service.settings.resume_id, "resume-1")
            self.assertEqual(store.get_selected_resume_id(), "resume-1")

    def test_settings_reports_connection_search_and_threshold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings("resume-1", "Hello", min_score=75),
                oauth_state="telegram-user-1",
                search_text="python",
                search_area="1",
            )

            message = service.handle_command("/settings")

            self.assertIn("hh.ru connected: no", message)
            self.assertIn("Search text: python", message)
            self.assertIn("Search area: 1", message)
            self.assertIn("Minimum score: 75", message)


if __name__ == "__main__":
    unittest.main()
