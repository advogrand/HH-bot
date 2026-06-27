import unittest
from urllib.parse import parse_qs, urlparse

from hh_bot.oauth import HhOAuthClient, HhOAuthConfig, OAuthToken


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
        self.posts: list[tuple[str, dict]] = []
        self.gets: list[tuple[str, dict]] = []

    async def post(self, url: str, data: dict) -> FakeResponse:
        self.posts.append((url, data))
        return FakeResponse(
            200,
            {
                "access_token": "access-1",
                "refresh_token": "refresh-1",
                "expires_in": 3600,
                "token_type": "bearer",
            },
        )

    async def get(self, url: str, headers: dict) -> FakeResponse:
        self.gets.append((url, headers))
        return FakeResponse(200, {"id": "me-1", "email": "me@example.com"})


class OAuthTests(unittest.IsolatedAsyncioTestCase):
    def test_build_authorization_url_contains_required_hh_params(self):
        client = HhOAuthClient(
            HhOAuthConfig(
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="https://example.com/oauth/hh/callback",
                user_agent="HHBot/0.1",
            )
        )

        url = client.build_authorization_url(state="telegram-user-1")

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "hh.ru")
        self.assertEqual(parsed.path, "/oauth/authorize")
        self.assertEqual(params["response_type"], ["code"])
        self.assertEqual(params["client_id"], ["client-1"])
        self.assertEqual(params["redirect_uri"], ["https://example.com/oauth/hh/callback"])
        self.assertEqual(params["state"], ["telegram-user-1"])

    async def test_exchange_code_posts_form_to_hh_token_endpoint(self):
        fake_http = FakeHttpClient()
        client = HhOAuthClient(
            HhOAuthConfig(
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="https://example.com/oauth/hh/callback",
                user_agent="HHBot/0.1",
            ),
            http_client=fake_http,
        )

        token = await client.exchange_code("code-1")

        self.assertIsInstance(token, OAuthToken)
        self.assertEqual(token.access_token, "access-1")
        self.assertEqual(token.refresh_token, "refresh-1")
        self.assertEqual(fake_http.posts[0][0], "https://api.hh.ru/token")
        self.assertEqual(
            fake_http.posts[0][1],
            {
                "grant_type": "authorization_code",
                "client_id": "client-1",
                "client_secret": "secret-1",
                "code": "code-1",
                "redirect_uri": "https://example.com/oauth/hh/callback",
            },
        )

    async def test_get_me_uses_bearer_token_and_user_agent(self):
        fake_http = FakeHttpClient()
        client = HhOAuthClient(
            HhOAuthConfig(
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="https://example.com/oauth/hh/callback",
                user_agent="HHBot/0.1",
            ),
            http_client=fake_http,
        )

        profile = await client.get_me("access-1")

        self.assertEqual(profile["id"], "me-1")
        self.assertEqual(fake_http.gets[0][0], "https://api.hh.ru/me")
        self.assertEqual(fake_http.gets[0][1]["Authorization"], "Bearer access-1")
        self.assertEqual(fake_http.gets[0][1]["User-Agent"], "HHBot/0.1")

    async def test_default_http_client_is_created_for_real_oauth_flow(self):
        client = HhOAuthClient(
            HhOAuthConfig(
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="https://example.com/oauth/hh/callback",
                user_agent="HHBot/0.1",
            )
        )

        http_client = client._require_http_client()

        self.assertIsNotNone(http_client)
        await http_client.aclose()


if __name__ == "__main__":
    unittest.main()
