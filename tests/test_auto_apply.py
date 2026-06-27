import tempfile
import unittest
from pathlib import Path

from hh_bot.auto_apply import AutoApplyRunner, is_remote_vacancy
from hh_bot.hh_apply import ApplyResult
from hh_bot.models import ScoreResult, UserSettings, Vacancy
from hh_bot.storage import SQLiteStore


class AutoApplyTests(unittest.IsolatedAsyncioTestCase):
    def test_remote_filter_accepts_remote_text(self):
        vacancy = Vacancy(
            id="1",
            name="Digital Designer",
            employer_name="Acme",
            url="https://hh.ru/vacancy/1",
            description="Можно работать удаленно из любого города",
        )

        self.assertTrue(is_remote_vacancy(vacancy))

    def test_remote_filter_rejects_office_text(self):
        vacancy = Vacancy(
            id="1",
            name="Digital Designer",
            employer_name="Acme",
            url="https://hh.ru/vacancy/1",
            area="Москва",
        )

        self.assertFalse(is_remote_vacancy(vacancy))

    async def test_auto_apply_skips_non_remote_and_respects_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            apply_runner = FakeApplyRunner()
            runner = AutoApplyRunner(
                store=store,
                apply_runner=apply_runner,
                daily_limit=1,
                delay_seconds=30,
                sleep=FakeSleep(),
            )
            settings = UserSettings(
                resume_id="resume-1",
                cover_letter="Hello",
                include_keywords=("дизайнер",),
                min_score=55,
            )

            summary = await runner.run(
                vacancies=[
                    _vacancy("1", "Digital дизайнер remote", "Удаленная работа"),
                    _vacancy("2", "Digital дизайнер office", "Офис Москва"),
                    _vacancy("3", "Digital дизайнер remote 2", "remote"),
                ],
                settings=settings,
                confirm=True,
            )

            self.assertEqual(summary.sent, 1)
            self.assertEqual(summary.skipped_non_remote, 1)
            self.assertEqual(summary.skipped_limit, 1)
            self.assertEqual(apply_runner.applied_ids, ["1"])

    async def test_auto_apply_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            apply_runner = FakeApplyRunner()
            runner = AutoApplyRunner(
                store=store,
                apply_runner=apply_runner,
                daily_limit=25,
                delay_seconds=30,
                sleep=FakeSleep(),
            )

            summary = await runner.run(
                vacancies=[_vacancy("1", "Digital Designer remote", "remote")],
                settings=UserSettings("resume-1", "Hello", include_keywords=("дизайнер",)),
                confirm=False,
            )

            self.assertEqual(summary.sent, 0)
            self.assertIn("Use /auto_apply confirm", summary.user_message)
            self.assertEqual(apply_runner.applied_ids, [])


class FakeApplyRunner:
    def __init__(self) -> None:
        self.applied_ids = []

    async def approve(self, *, vacancy, settings, score):
        self.applied_ids.append(vacancy.id)
        return ApplyResult(ok=True, status="sent", user_message="sent")


class FakeSleep:
    def __init__(self) -> None:
        self.calls = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _vacancy(vacancy_id: str, title: str, description: str) -> Vacancy:
    return Vacancy(
        id=vacancy_id,
        name=title,
        employer_name="Acme",
        url=f"https://hh.ru/vacancy/{vacancy_id}",
        description=description,
    )


if __name__ == "__main__":
    unittest.main()
