import tempfile
import unittest
from pathlib import Path

from hh_bot.config import load_dotenv_file


class ConfigTests(unittest.TestCase):
    def test_load_dotenv_file_reads_simple_key_values_without_overriding(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "TELEGRAM_BOT_TOKEN=from-file\n"
                "DEFAULT_COVER_LETTER='Hello there'\n"
                "# comment\n",
                encoding="utf-8",
            )

            values = load_dotenv_file(env_path, existing={"TELEGRAM_BOT_TOKEN": "existing"})

            self.assertEqual(values["TELEGRAM_BOT_TOKEN"], "existing")
            self.assertEqual(values["DEFAULT_COVER_LETTER"], "Hello there")


if __name__ == "__main__":
    unittest.main()
