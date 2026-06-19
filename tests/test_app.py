import tempfile
import unittest
from pathlib import Path

from hh_bot.app import build_service
from hh_bot.config import Settings


class AppTests(unittest.TestCase):
    def test_build_service_initializes_store_and_default_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = Settings(
                telegram_bot_token="",
                hh_client_id="",
                hh_client_secret="",
                hh_redirect_uri="http://localhost:8000/oauth/hh/callback",
                hh_user_agent="HHBot/0.1 (you@example.com)",
                database_path=str(Path(temp_dir) / "bot.sqlite3"),
                default_min_score=77,
                run_telegram_polling=False,
                default_resume_id="resume-x",
                default_cover_letter="Hello from settings",
                include_keywords=("python", "fastapi"),
                exclude_keywords=("php",),
                oauth_start_url="http://localhost:8000/oauth/hh/start",
                oauth_state="telegram-user-1",
                run_oauth_server=False,
                hh_search_text="python",
                hh_search_area="1",
                hh_search_per_page=10,
            )

            service = build_service(settings)

            self.assertEqual(service.settings.resume_id, "resume-x")
            self.assertEqual(service.settings.min_score, 77)
            self.assertEqual(service.settings.include_keywords, ("python", "fastapi"))
            self.assertIn("http://localhost:8000/oauth/hh/start", service.handle_command("/connect"))
            self.assertEqual(service.store.list_audit_entries(), [])


if __name__ == "__main__":
    unittest.main()
