import unittest

from hh_bot.hh_browser_login import _looks_logged_in


class BrowserLoginTests(unittest.TestCase):
    def test_detects_logged_in_page(self):
        page = FakePage("Мои резюме Отклики Профиль")

        self.assertTrue(_looks_logged_in(page))

    def test_detects_login_page(self):
        page = FakePage("Войти Регистрация Авторизация")

        self.assertFalse(_looks_logged_in(page))


class FakePage:
    def __init__(self, text: str) -> None:
        self.text = text

    def locator(self, selector: str):
        return FakeBody(self.text)


class FakeBody:
    def __init__(self, text: str) -> None:
        self.text = text

    def inner_text(self) -> str:
        return self.text


if __name__ == "__main__":
    unittest.main()
