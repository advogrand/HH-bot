import tempfile
import unittest
from pathlib import Path

from hh_bot.hh_resume_runner import HhResumeRunner
from hh_bot.models import Resume
from hh_bot.oauth import OAuthToken
from hh_bot.storage import SQLiteStore


class FakeResumeClientFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, *, access_token: str, user_agent: str):
        self.calls.append((access_token, user_agent))
        return FakeResumeClient()


class FakeResumeClient:
    async def list_mine(self):
        return [Resume(id="resume-1", title="Python Developer", url="https://api.hh.ru/resumes/1")]


class HhResumeRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_loads_token_and_fetches_resumes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            store.save_oauth_token(
                "telegram-user-1",
                OAuthToken("access-1", "refresh-1", 3600, "bearer"),
            )
            factory = FakeResumeClientFactory()
            runner = HhResumeRunner(
                store=store,
                oauth_state="telegram-user-1",
                user_agent="HHBot/0.1",
                resume_client_factory=factory,
            )

            resumes = await runner.fetch_resumes()

            self.assertEqual(resumes[0].id, "resume-1")
            self.assertEqual(factory.calls, [("access-1", "HHBot/0.1")])

    async def test_missing_token_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            runner = HhResumeRunner(
                store=store,
                oauth_state="telegram-user-1",
                user_agent="HHBot/0.1",
            )

            self.assertEqual(await runner.fetch_resumes(), [])


if __name__ == "__main__":
    unittest.main()
