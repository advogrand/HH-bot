import tempfile
import unittest
from pathlib import Path

from hh_bot.models import AuditEntry
from hh_bot.storage import SQLiteStore


class StorageTests(unittest.TestCase):
    def test_records_dry_run_without_marking_real_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "bot.sqlite3"
            store = SQLiteStore(db_path)
            store.initialize()

            self.assertFalse(store.has_response("resume-1", "vacancy-1"))

            entry = AuditEntry(
                vacancy_id="vacancy-1",
                vacancy_url="https://hh.ru/vacancy/1",
                vacancy_title="Python Developer",
                employer_name="Acme",
                resume_id="resume-1",
                score=88,
                reason="matched keywords: python",
                cover_letter="Hello",
                user_action="approved",
                api_status="dry_run",
            )

            store.record_audit(entry)

            self.assertFalse(store.has_response("resume-1", "vacancy-1"))
            rows = store.list_audit_entries()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["vacancy_id"], "vacancy-1")
            self.assertEqual(rows[0]["api_status"], "dry_run")

    def test_sent_response_prevents_duplicate_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "bot.sqlite3"
            store = SQLiteStore(db_path)
            store.initialize()

            entry = AuditEntry(
                vacancy_id="vacancy-1",
                vacancy_url="https://hh.ru/vacancy/1",
                vacancy_title="Python Developer",
                employer_name="Acme",
                resume_id="resume-1",
                score=88,
                reason="matched keywords: python",
                cover_letter="Hello",
                user_action="approved",
                api_status="sent",
            )

            store.record_audit(entry)

            self.assertTrue(store.has_response("resume-1", "vacancy-1"))

    def test_saves_and_loads_selected_resume_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "bot.sqlite3"
            store = SQLiteStore(db_path)
            store.initialize()

            self.assertIsNone(store.get_selected_resume_id())

            store.save_selected_resume_id("resume-1")

            self.assertEqual(store.get_selected_resume_id(), "resume-1")

    def test_saves_and_loads_user_tunable_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "bot.sqlite3"
            store = SQLiteStore(db_path)
            store.initialize()

            self.assertIsNone(store.get_search_text())
            self.assertIsNone(store.get_min_score())
            self.assertIsNone(store.get_cover_letter())

            store.save_search_text("python backend")
            store.save_min_score(72)
            store.save_cover_letter("Здравствуйте, готов обсудить вакансию.")

            self.assertEqual(store.get_search_text(), "python backend")
            self.assertEqual(store.get_min_score(), 72)
            self.assertEqual(
                store.get_cover_letter(),
                "Здравствуйте, готов обсудить вакансию.",
            )

    def test_saves_and_loads_keyword_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "bot.sqlite3"
            store = SQLiteStore(db_path)
            store.initialize()

            self.assertIsNone(store.get_include_keywords())
            self.assertIsNone(store.get_exclude_keywords())

            store.save_include_keywords(("дизайнер", "графическ", "figma"))
            store.save_exclude_keywords(("python", "backend"))

            self.assertEqual(store.get_include_keywords(), ("дизайнер", "графическ", "figma"))
            self.assertEqual(store.get_exclude_keywords(), ("python", "backend"))


if __name__ == "__main__":
    unittest.main()
