import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from hh_bot.oauth import HhOAuthConfig, OAuthToken
from hh_bot.oauth_web import create_oauth_app
from hh_bot.storage import SQLiteStore


class FakeOAuthClient:
    def __init__(self) -> None:
        self.exchanged_codes: list[str] = []

    async def exchange_code(self, code: str) -> OAuthToken:
        self.exchanged_codes.append(code)
        return OAuthToken(
            access_token="access-1",
            refresh_token="refresh-1",
            expires_in=3600,
            token_type="bearer",
        )


class OAuthWebTests(unittest.TestCase):
    def test_callback_exchanges_code_and_saves_token(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            fake_oauth = FakeOAuthClient()
            app = create_oauth_app(store=store, oauth_client=fake_oauth)
            client = TestClient(app)

            response = client.get("/oauth/hh/callback?code=code-1&state=telegram-user-1")

            self.assertEqual(response.status_code, 200)
            self.assertIn("hh.ru account connected", response.text)
            self.assertEqual(fake_oauth.exchanged_codes, ["code-1"])
            self.assertEqual(store.get_oauth_token("telegram-user-1").access_token, "access-1")

    def test_start_redirects_to_hh_authorization_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            config = HhOAuthConfig(
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="https://example.com/oauth/hh/callback",
                user_agent="HHBot/0.1",
            )
            app = create_oauth_app(store=store, oauth_config=config)
            client = TestClient(app)

            response = client.get("/oauth/hh/start?state=telegram-user-1", follow_redirects=False)

            self.assertEqual(response.status_code, 307)
            self.assertIn("https://hh.ru/oauth/authorize", response.headers["location"])


if __name__ == "__main__":
    unittest.main()
