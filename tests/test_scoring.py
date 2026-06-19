import unittest

from hh_bot.models import UserSettings, Vacancy
from hh_bot.scoring import evaluate_vacancy


class ScoringTests(unittest.TestCase):
    def test_rejects_vacancy_with_excluded_keyword(self):
        vacancy = Vacancy(
            id="1",
            name="Senior PHP Developer",
            employer_name="Acme",
            url="https://hh.ru/vacancy/1",
            description="Legacy PHP project",
        )
        settings = UserSettings(
            resume_id="resume-1",
            cover_letter="Hello",
            include_keywords=("python",),
            exclude_keywords=("php",),
        )

        result = evaluate_vacancy(vacancy, settings, already_applied=False)

        self.assertFalse(result.is_match)
        self.assertEqual(result.score, 0)
        self.assertIn("excluded keyword: php", result.reason)

    def test_rejects_already_applied_vacancy(self):
        vacancy = Vacancy(
            id="2",
            name="Python Developer",
            employer_name="Acme",
            url="https://hh.ru/vacancy/2",
            description="Python and FastAPI",
        )
        settings = UserSettings(resume_id="resume-1", cover_letter="Hello")

        result = evaluate_vacancy(vacancy, settings, already_applied=True)

        self.assertFalse(result.is_match)
        self.assertEqual(result.score, 0)
        self.assertEqual(result.reason, "already applied")

    def test_scores_matching_keyword_vacancy(self):
        vacancy = Vacancy(
            id="3",
            name="Python Backend Developer",
            employer_name="Acme",
            url="https://hh.ru/vacancy/3",
            description="FastAPI, SQLite, Telegram bot automation",
            schedule="remote",
        )
        settings = UserSettings(
            resume_id="resume-1",
            cover_letter="Hello",
            include_keywords=("python", "fastapi", "telegram"),
            preferred_schedule="remote",
            min_score=60,
        )

        result = evaluate_vacancy(vacancy, settings, already_applied=False)

        self.assertTrue(result.is_match)
        self.assertGreaterEqual(result.score, 60)
        self.assertIn("matched keywords", result.reason)

    def test_single_include_keyword_match_can_pass_default_threshold(self):
        vacancy = Vacancy(
            id="4",
            name="Python Developer",
            employer_name="Acme",
            url="https://hh.ru/vacancy/4",
            description="Backend services",
        )
        settings = UserSettings(
            resume_id="resume-1",
            cover_letter="Hello",
            include_keywords=("python", "fastapi", "telegram"),
            min_score=60,
        )

        result = evaluate_vacancy(vacancy, settings, already_applied=False)

        self.assertTrue(result.is_match)
        self.assertGreaterEqual(result.score, 60)
        self.assertEqual(result.reason, "matched keywords: python")


if __name__ == "__main__":
    unittest.main()
