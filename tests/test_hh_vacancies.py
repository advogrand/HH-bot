import unittest

from hh_bot.hh_vacancies import (
    HhVacancyClient,
    HhVacancySearchError,
    SearchQuery,
    map_vacancy,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttpClient:
    def __init__(self) -> None:
        self.gets: list[tuple[str, dict, dict]] = []

    async def get(self, url: str, *, headers: dict, params: dict) -> FakeResponse:
        self.gets.append((url, headers, params))
        return FakeResponse(
            200,
            {
                "items": [
                    {
                        "id": "1",
                        "name": "Python Developer",
                        "alternate_url": "https://hh.ru/vacancy/1",
                        "snippet": {"requirement": "Python", "responsibility": "FastAPI"},
                        "salary": {"from": 200000, "to": None, "currency": "RUR"},
                        "area": {"name": "Moscow"},
                        "schedule": {"id": "remote", "name": "Remote"},
                        "employment": {"id": "full", "name": "Full time"},
                        "relations": ["favorited"],
                        "employer": {"name": "Acme"},
                    }
                ]
            },
        )


class ForbiddenHttpClient:
    async def get(self, url: str, *, headers: dict, params: dict) -> FakeResponse:
        return FakeResponse(403, {"errors": [{"type": "forbidden"}]})


class HhVacancyTests(unittest.IsolatedAsyncioTestCase):
    def test_map_vacancy_extracts_applicant_fields(self):
        vacancy = map_vacancy(
            {
                "id": "1",
                "name": "Python Developer",
                "alternate_url": "https://hh.ru/vacancy/1",
                "snippet": {"requirement": "Python", "responsibility": "FastAPI"},
                "salary": {"from": 200000, "to": 250000, "currency": "RUR"},
                "area": {"name": "Moscow"},
                "schedule": {"id": "remote"},
                "employment": {"id": "full"},
                "relations": ["got_response"],
                "employer": {"name": "Acme"},
            }
        )

        self.assertEqual(vacancy.id, "1")
        self.assertEqual(vacancy.employer_name, "Acme")
        self.assertEqual(vacancy.url, "https://hh.ru/vacancy/1")
        self.assertEqual(vacancy.salary, "200000-250000 RUR")
        self.assertEqual(vacancy.area, "Moscow")
        self.assertEqual(vacancy.schedule, "remote")
        self.assertEqual(vacancy.employment, "full")
        self.assertEqual(vacancy.relations, ("got_response",))
        self.assertIn("Python", vacancy.description)

    async def test_search_vacancies_calls_hh_api_with_token_and_query(self):
        fake_http = FakeHttpClient()
        client = HhVacancyClient(
            access_token="access-1",
            user_agent="HHBot/0.1",
            http_client=fake_http,
        )

        vacancies = await client.search_vacancies(
            SearchQuery(text="python", area="1", per_page=5, page=0)
        )

        self.assertEqual(len(vacancies), 1)
        self.assertEqual(vacancies[0].name, "Python Developer")
        self.assertEqual(fake_http.gets[0][0], "https://api.hh.ru/vacancies")
        self.assertEqual(fake_http.gets[0][1]["Authorization"], "Bearer access-1")
        self.assertEqual(fake_http.gets[0][1]["User-Agent"], "HHBot/0.1")
        self.assertEqual(
            fake_http.gets[0][2],
            {"text": "python", "area": "1", "per_page": 5, "page": 0},
        )

    async def test_search_vacancies_without_token_omits_authorization_header(self):
        fake_http = FakeHttpClient()
        client = HhVacancyClient(
            access_token=None,
            user_agent="HHBot/0.1",
            http_client=fake_http,
        )

        vacancies = await client.search_vacancies(SearchQuery(text="python"))

        self.assertEqual(len(vacancies), 1)
        self.assertNotIn("Authorization", fake_http.gets[0][1])
        self.assertEqual(fake_http.gets[0][1]["User-Agent"], "HHBot/0.1")

    async def test_search_vacancies_maps_forbidden_response_to_search_error(self):
        client = HhVacancyClient(
            access_token=None,
            user_agent="HHBot/0.1",
            http_client=ForbiddenHttpClient(),
        )

        with self.assertRaisesRegex(HhVacancySearchError, "hh.ru API denied vacancy search"):
            await client.search_vacancies(SearchQuery(text="python"))


if __name__ == "__main__":
    unittest.main()
