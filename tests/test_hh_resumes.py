import unittest

from hh_bot.hh_resumes import HhResumeClient, map_resume


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
        self.gets: list[tuple[str, dict]] = []

    async def get(self, url: str, *, headers: dict) -> FakeResponse:
        self.gets.append((url, headers))
        return FakeResponse(
            200,
            {
                "items": [
                    {
                        "id": "resume-1",
                        "title": "Python Developer",
                        "url": "https://api.hh.ru/resumes/resume-1",
                    }
                ]
            },
        )


class HhResumeTests(unittest.IsolatedAsyncioTestCase):
    def test_map_resume_extracts_short_resume_fields(self):
        resume = map_resume(
            {
                "id": "resume-1",
                "title": "Python Developer",
                "url": "https://api.hh.ru/resumes/resume-1",
            }
        )

        self.assertEqual(resume.id, "resume-1")
        self.assertEqual(resume.title, "Python Developer")
        self.assertEqual(resume.url, "https://api.hh.ru/resumes/resume-1")

    async def test_list_mine_uses_bearer_token_and_user_agent(self):
        fake_http = FakeHttpClient()
        client = HhResumeClient(
            access_token="access-1",
            user_agent="HHBot/0.1",
            http_client=fake_http,
        )

        resumes = await client.list_mine()

        self.assertEqual(resumes[0].id, "resume-1")
        self.assertEqual(fake_http.gets[0][0], "https://api.hh.ru/resumes/mine")
        self.assertEqual(fake_http.gets[0][1]["Authorization"], "Bearer access-1")
        self.assertEqual(fake_http.gets[0][1]["User-Agent"], "HHBot/0.1")


if __name__ == "__main__":
    unittest.main()
