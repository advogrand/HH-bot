import unittest

from hh_bot.models import ScoreResult, UserSettings, Vacancy
from hh_bot.telegram_messages import render_candidate_message


class TelegramMessageTests(unittest.TestCase):
    def test_candidate_message_contains_safe_approval_context(self):
        vacancy = Vacancy(
            id="42",
            name="Python Developer",
            employer_name="Acme",
            url="https://hh.ru/vacancy/42",
            salary="200000 RUR",
            area="Moscow",
            schedule="remote",
            employment="full",
        )
        score = ScoreResult(is_match=True, score=91, reason="matched keywords: python")
        settings = UserSettings(resume_id="resume-1", cover_letter="Short honest letter")

        message = render_candidate_message(vacancy, score, settings)

        self.assertIn("Python Developer", message)
        self.assertIn("Acme", message)
        self.assertIn("91", message)
        self.assertIn("Short honest letter", message)
        self.assertIn("/approve 42", message)
        self.assertIn("/reject 42", message)


if __name__ == "__main__":
    unittest.main()
