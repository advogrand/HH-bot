import tempfile
import unittest
from pathlib import Path

from hh_bot.hh_apply import ApplyResult
from hh_bot.hh_apply_runner import HhApplyRunner
from hh_bot.models import ScoreResult, UserSettings, Vacancy
from hh_bot.oauth import OAuthToken
from hh_bot.storage import SQLiteStore


class FakeApplyClientFactory:
    def __init__(self, result: ApplyResult) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []
        self.requests = []

    def __call__(self, *, access_token: str, user_agent: str):
        self.calls.append((access_token, user_agent))
        return FakeApplyClient(self)


class FakeApplyClient:
    def __init__(self, factory: FakeApplyClientFactory) -> None:
        self.factory = factory

    async def apply_to_vacancy(self, request):
        self.factory.requests.append(request)
        return self.factory.result


class HhApplyRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_real_apply_records_dry_run_without_calling_hh(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            factory = FakeApplyClientFactory(ApplyResult(ok=True, status="sent"))
            runner = HhApplyRunner(
                store=store,
                oauth_state="telegram-user-1",
                user_agent="HHBot/0.1",
                real_apply_enabled=False,
                apply_client_factory=factory,
            )

            result = await runner.approve(
                vacancy=_vacancy(),
                settings=UserSettings("resume-1", "Hello"),
                score=ScoreResult(True, 90, "matched keywords: python"),
            )

            self.assertEqual(result.status, "dry_run")
            self.assertEqual(factory.calls, [])
            self.assertTrue(store.has_response("resume-1", "vacancy-1"))
            self.assertEqual(store.list_audit_entries()[0]["api_status"], "dry_run")

    async def test_enabled_real_apply_uses_saved_token_and_records_sent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            store.save_oauth_token(
                "telegram-user-1",
                OAuthToken("access-1", "refresh-1", 3600, "bearer"),
            )
            factory = FakeApplyClientFactory(ApplyResult(ok=True, status="sent"))
            runner = HhApplyRunner(
                store=store,
                oauth_state="telegram-user-1",
                user_agent="HHBot/0.1",
                real_apply_enabled=True,
                apply_client_factory=factory,
            )

            result = await runner.approve(
                vacancy=_vacancy(),
                settings=UserSettings("resume-1", "Hello"),
                score=ScoreResult(True, 90, "matched keywords: python"),
            )

            self.assertEqual(result.status, "sent")
            self.assertEqual(factory.calls, [("access-1", "HHBot/0.1")])
            self.assertEqual(factory.requests[0].resume_id, "resume-1")
            self.assertEqual(factory.requests[0].vacancy_id, "vacancy-1")
            self.assertEqual(store.list_audit_entries()[0]["api_status"], "sent")

    async def test_enabled_real_apply_without_token_does_not_record_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            runner = HhApplyRunner(
                store=store,
                oauth_state="telegram-user-1",
                user_agent="HHBot/0.1",
                real_apply_enabled=True,
            )

            result = await runner.approve(
                vacancy=_vacancy(),
                settings=UserSettings("resume-1", "Hello"),
                score=ScoreResult(True, 90, "matched keywords: python"),
            )

            self.assertEqual(result.status, "not_connected")
            self.assertFalse(store.has_response("resume-1", "vacancy-1"))


def _vacancy() -> Vacancy:
    return Vacancy(
        id="vacancy-1",
        name="Python Developer",
        employer_name="Acme",
        url="https://hh.ru/vacancy/1",
        description="Python",
    )


if __name__ == "__main__":
    unittest.main()
