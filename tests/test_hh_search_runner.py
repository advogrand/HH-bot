import tempfile
import unittest
from pathlib import Path

from hh_bot.hh_search_runner import HhSearchRunner
from hh_bot.models import UserSettings, Vacancy
from hh_bot.oauth import OAuthToken
from hh_bot.storage import SQLiteStore


class FakeVacancyClientFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[str | None, str]] = []

    def __call__(self, *, access_token: str | None, user_agent: str):
        self.calls.append((access_token, user_agent))
        return FakeVacancyClient()


class FakeVacancyClient:
    async def search_vacancies(self, query):
        return [
            Vacancy(
                id="1",
                name="Python Developer",
                employer_name="Acme",
                url="https://hh.ru/vacancy/1",
                description="Python FastAPI",
            )
        ]


class HhSearchRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_loads_token_and_updates_bot_service_vacancies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            store.save_oauth_token(
                "telegram-user-1",
                OAuthToken(
                    access_token="access-1",
                    refresh_token="refresh-1",
                    expires_in=3600,
                    token_type="bearer",
                ),
            )
            factory = FakeVacancyClientFactory()
            runner = HhSearchRunner(
                store=store,
                oauth_state="telegram-user-1",
                user_agent="HHBot/0.1",
                search_text="python",
                area="1",
                vacancy_client_factory=factory,
            )

            vacancies = await runner.fetch_vacancies()

            self.assertEqual(vacancies[0].name, "Python Developer")
            self.assertEqual(factory.calls, [("access-1", "HHBot/0.1")])

    async def test_missing_token_uses_public_vacancy_search(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            factory = FakeVacancyClientFactory()
            runner = HhSearchRunner(
                store=store,
                oauth_state="telegram-user-1",
                user_agent="HHBot/0.1",
                search_text="python",
                vacancy_client_factory=factory,
            )

            vacancies = await runner.fetch_vacancies()

            self.assertEqual(vacancies[0].name, "Python Developer")
            self.assertEqual(factory.calls, [(None, "HHBot/0.1")])


if __name__ == "__main__":
    unittest.main()
