import unittest

from hh_bot.hh_errors import HhApiError, map_hh_error


class HhErrorTests(unittest.TestCase):
    def test_maps_known_limit_error_to_user_message(self):
        error = map_hh_error(403, [{"type": "negotiations", "value": "limit_exceeded"}])

        self.assertIsInstance(error, HhApiError)
        self.assertEqual(error.status_code, 403)
        self.assertEqual(error.value, "limit_exceeded")
        self.assertIn("limit", error.user_message.lower())

    def test_maps_captcha_error_with_fallback_url(self):
        error = map_hh_error(
            403,
            [
                {
                    "type": "captcha_required",
                    "value": "captcha_required",
                    "fallback_url": "https://hh.ru/account/captcha",
                }
            ],
        )

        self.assertEqual(error.value, "captcha_required")
        self.assertEqual(error.fallback_url, "https://hh.ru/account/captcha")
        self.assertIn("captcha", error.user_message.lower())

    def test_maps_unknown_error_without_crashing(self):
        error = map_hh_error(500, [{"type": "server", "value": "unknown"}])

        self.assertEqual(error.status_code, 500)
        self.assertEqual(error.type, "server")
        self.assertEqual(error.value, "unknown")
        self.assertIn("hh.ru API error", error.user_message)


if __name__ == "__main__":
    unittest.main()
