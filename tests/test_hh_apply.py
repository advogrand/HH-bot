import unittest

from hh_bot.hh_apply import ApplyRequest, HhApplyClient


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttpClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.posts: list[tuple[str, dict, dict]] = []

    async def post(self, url: str, *, headers: dict, data: dict) -> FakeResponse:
        self.posts.append((url, headers, data))
        return self.response


class HhApplyTests(unittest.IsolatedAsyncioTestCase):
    async def test_apply_to_vacancy_posts_resume_vacancy_and_message(self):
        fake_http = FakeHttpClient(FakeResponse(201))
        client = HhApplyClient(
            access_token="access-1",
            user_agent="HHBot/0.1",
            http_client=fake_http,
        )

        result = await client.apply_to_vacancy(
            ApplyRequest(
                resume_id="resume-1",
                vacancy_id="vacancy-1",
                message="Hello",
            )
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.status, "sent")
        self.assertEqual(fake_http.posts[0][0], "https://api.hh.ru/negotiations")
        self.assertEqual(fake_http.posts[0][1]["Authorization"], "Bearer access-1")
        self.assertEqual(fake_http.posts[0][1]["User-Agent"], "HHBot/0.1")
        self.assertEqual(
            fake_http.posts[0][2],
            {"resume_id": "resume-1", "vacancy_id": "vacancy-1", "message": "Hello"},
        )

    async def test_apply_to_vacancy_maps_hh_error(self):
        fake_http = FakeHttpClient(
            FakeResponse(
                403,
                {"errors": [{"type": "negotiations", "value": "already_applied"}]},
            )
        )
        client = HhApplyClient(
            access_token="access-1",
            user_agent="HHBot/0.1",
            http_client=fake_http,
        )

        result = await client.apply_to_vacancy(
            ApplyRequest(
                resume_id="resume-1",
                vacancy_id="vacancy-1",
                message="Hello",
            )
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error.value, "already_applied")


if __name__ == "__main__":
    unittest.main()
