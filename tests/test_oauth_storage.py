import tempfile
import unittest
from pathlib import Path

from hh_bot.oauth import OAuthToken
from hh_bot.storage import SQLiteStore


class OAuthStorageTests(unittest.TestCase):
    def test_saves_and_loads_oauth_token_for_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "bot.sqlite3")
            store.initialize()
            token = OAuthToken(
                access_token="access-1",
                refresh_token="refresh-1",
                expires_in=3600,
                token_type="bearer",
            )

            store.save_oauth_token("state-1", token)
            loaded = store.get_oauth_token("state-1")

            self.assertEqual(loaded, token)


if __name__ == "__main__":
    unittest.main()
