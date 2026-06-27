import tempfile
import unittest
from pathlib import Path

from hh_bot.bot_service import BotService
from hh_bot.models import AuditEntry, Resume, UserSettings, Vacancy
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

    def test_audit_reports_recent_entries(self):
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

            service.handle_command("/approve 1")
            message = service.handle_command("/audit")

            self.assertIn("Last 1 audit entries", message)
            self.assertIn("Python Developer", message)
            self.assertIn("Status: dry_run", message)
            self.assertIn("https://hh.ru/vacancy/1", message)

    def test_audit_reports_error_details(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            store.record_audit(
                AuditEntry(
                    vacancy_id="1",
                    vacancy_url="https://hh.ru/vacancy/1",
                    vacancy_title="Designer",
                    employer_name="Acme",
                    resume_id="resume-1",
                    score=64,
                    reason="matched keywords: designer",
                    cover_letter="Hello",
                    user_action="approved",
                    api_status="failed",
                    api_error_type="test_required",
                    api_error_value="test_required",
                )
            )
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))

            message = service.handle_command("/audit")

            self.assertIn("Status: failed", message)
            self.assertIn("Error: test_required / test_required", message)

    def test_audit_reports_empty_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))

            message = service.handle_command("/audit")

            self.assertIn("Audit is empty", message)

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

    def test_search_reports_near_misses_when_browser_cards_do_not_pass_filters(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings(
                    resume_id="resume-1",
                    cover_letter="Hello",
                    include_keywords=("python", "fastapi", "telegram"),
                    min_score=90,
                ),
                vacancies=[
                    Vacancy(
                        id="1",
                        name="Python Developer",
                        employer_name="Acme",
                        url="https://hh.ru/vacancy/1",
                        description="Backend services",
                    )
                ],
            )

            message = service.handle_command("/search")

            self.assertIn("Found 1 vacancies, but none passed filters", message)
            self.assertIn("Python Developer", message)
            self.assertIn("matched keywords: python", message)

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
            self.assertFalse(store.has_response("resume-1", "1"))
            self.assertEqual(store.list_audit_entries()[0]["api_status"], "dry_run")

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

    def test_set_search_updates_runtime_and_persists_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings("resume-1", "Hello"),
                search_text="python",
            )

            message = service.handle_command("/set_search python backend")

            self.assertIn("Search text updated: python backend", message)
            self.assertEqual(service.search_text, "python backend")
            self.assertEqual(store.get_search_text(), "python backend")

    def test_set_score_validates_range_and_persists_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(
                store=store,
                settings=UserSettings("resume-1", "Hello", min_score=60),
            )

            invalid = service.handle_command("/set_score 101")
            valid = service.handle_command("/set_score 72")

            self.assertIn("Use /set_score with a number from 0 to 100.", invalid)
            self.assertIn("Minimum score updated: 72", valid)
            self.assertEqual(service.settings.min_score, 72)
            self.assertEqual(store.get_min_score(), 72)

    def test_set_resume_updates_runtime_and_persists_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))

            message = service.handle_command("/set_resume resume-2")

            self.assertIn("Resume updated: resume-2", message)
            self.assertEqual(service.settings.resume_id, "resume-2")
            self.assertEqual(store.get_selected_resume_id(), "resume-2")

    def test_set_letter_updates_runtime_and_persists_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))

            message = service.handle_command("/set_letter Здравствуйте, готов обсудить.")

            self.assertIn("Cover letter updated.", message)
            self.assertEqual(service.settings.cover_letter, "Здравствуйте, готов обсудить.")
            self.assertEqual(store.get_cover_letter(), "Здравствуйте, готов обсудить.")

    def test_set_include_updates_runtime_and_persists_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))

            message = service.handle_command("/set_include дизайнер, графическ, figma")

            self.assertIn("Include keywords updated", message)
            self.assertEqual(service.settings.include_keywords, ("дизайнер", "графическ", "figma"))
            self.assertEqual(store.get_include_keywords(), ("дизайнер", "графическ", "figma"))

    def test_set_exclude_updates_runtime_and_persists_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            service = BotService(store=store, settings=UserSettings("resume-1", "Hello"))

            message = service.handle_command("/set_exclude python, backend")

            self.assertIn("Exclude keywords updated", message)
            self.assertEqual(service.settings.exclude_keywords, ("python", "backend"))
            self.assertEqual(store.get_exclude_keywords(), ("python", "backend"))


if __name__ == "__main__":
    unittest.main()
