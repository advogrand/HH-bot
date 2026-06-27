import unittest

from hh_bot.hh_browser_apply import apply_visible_page
from hh_bot.models import UserSettings, Vacancy


class BrowserApplyTests(unittest.TestCase):
    def test_browser_apply_success_returns_sent(self):
        page = FakePage(
            text="Вакансия дизайнер",
            selectors={
                '[data-qa="vacancy-response-link-top"]': FakeLocator(visible=True),
                '[data-qa="vacancy-response-popup-form-letter-input"]': FakeLocator(visible=True),
                '[data-qa="vacancy-response-submit-popup"]': FakeLocator(visible=True, after_click_text="Отклик отправлен"),
            },
        )

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertTrue(result.ok)
        self.assertEqual(result.status, "sent")
        self.assertEqual(page.selectors['[data-qa="vacancy-response-popup-form-letter-input"]'].filled, "Hello")

    def test_browser_apply_stops_on_captcha(self):
        page = FakePage(text="Пожалуйста, пройдите captcha")

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.value, "captcha_required")

    def test_browser_apply_stops_on_questions(self):
        page = FakePage(
            text="Вакансия дизайнер",
            selectors={
                '[data-qa="vacancy-response-link-top"]': FakeLocator(
                    visible=True,
                    after_click_text="Работодатель просит ответить на вопросы",
                ),
            },
        )

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.value, "questions_required")

    def test_browser_apply_stops_when_response_button_missing(self):
        page = FakePage(text="Вакансия дизайнер")

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.value, "response_unavailable")


class FakePage:
    def __init__(self, *, text: str, selectors: dict[str, "FakeLocator"] | None = None) -> None:
        self.text = text
        self.selectors = selectors or {}

    def locator(self, selector: str):
        if selector == "body":
            return FakeBodyLocator(self)
        locator = self.selectors.get(selector) or FakeLocator(visible=False)
        locator.page = self
        return locator

    def wait_for_timeout(self, milliseconds: int) -> None:
        return


class FakeBodyLocator:
    def __init__(self, page: FakePage) -> None:
        self.page = page

    def inner_text(self) -> str:
        return self.page.text


class FakeLocator:
    def __init__(self, *, visible: bool, after_click_text: str = "") -> None:
        self.visible = visible
        self.after_click_text = after_click_text
        self.filled = ""
        self.page: FakePage | None = None

    @property
    def first(self):
        return self

    def count(self) -> int:
        return 1 if self.visible else 0

    def is_visible(self) -> bool:
        return self.visible

    def click(self) -> None:
        if self.after_click_text and self.page is not None:
            self.page.text = self.after_click_text

    def fill(self, value: str) -> None:
        self.filled = value


def _vacancy() -> Vacancy:
    return Vacancy(
        id="vacancy-1",
        name="Designer",
        employer_name="Acme",
        url="https://hh.ru/vacancy/vacancy-1",
        description="designer",
    )


if __name__ == "__main__":
    unittest.main()
