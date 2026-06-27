import tempfile
import unittest
from pathlib import Path

from hh_bot.hh_browser_apply import HhBrowserApplyConfig, apply_visible_page, run_browser_apply
from hh_bot.models import UserSettings, Vacancy


class BrowserApplyTests(unittest.TestCase):
    def test_browser_apply_success_returns_sent(self):
        page = FakePage(
            text="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0434\u0438\u0437\u0430\u0439\u043d\u0435\u0440",
            selectors={
                '[data-qa="vacancy-response-link-top"]': FakeLocator(visible=True),
                '[data-qa="vacancy-response-letter-toggle"]': FakeLocator(
                    visible=True,
                    reveal_selector='[data-qa="vacancy-response-popup-form-letter-input"]',
                ),
                '[data-qa="vacancy-response-popup-form-letter-input"]': FakeLocator(visible=False),
                '[data-qa="vacancy-response-submit-popup"]': FakeLocator(
                    visible=True,
                    after_click_text="\u041e\u0442\u043a\u043b\u0438\u043a \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d",
                ),
            },
        )

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertTrue(result.ok)
        self.assertEqual(result.status, "sent")
        self.assertEqual(page.selectors['[data-qa="vacancy-response-popup-form-letter-input"]'].filled, "Hello")

    def test_browser_apply_requires_sent_confirmation(self):
        page = FakePage(
            text="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0434\u0438\u0437\u0430\u0439\u043d\u0435\u0440",
            selectors={
                '[data-qa="vacancy-response-link-top"]': FakeLocator(visible=True),
                '[data-qa="vacancy-response-popup-form-letter-input"]': FakeLocator(visible=True),
                '[data-qa="vacancy-response-submit-popup"]': FakeLocator(visible=True),
            },
        )

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.value, "confirmation_missing")

    def test_browser_apply_stops_on_captcha(self):
        page = FakePage(text="\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u043f\u0440\u043e\u0439\u0434\u0438\u0442\u0435 captcha")

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.value, "captcha_required")

    def test_browser_apply_stops_on_questions(self):
        page = FakePage(
            text="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0434\u0438\u0437\u0430\u0439\u043d\u0435\u0440",
            selectors={
                '[data-qa="vacancy-response-link-top"]': FakeLocator(
                    visible=True,
                    after_click_text="\u0420\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044c \u043f\u0440\u043e\u0441\u0438\u0442 \u043e\u0442\u0432\u0435\u0442\u0438\u0442\u044c \u043d\u0430 \u0432\u043e\u043f\u0440\u043e\u0441\u044b",
                ),
            },
        )

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.value, "questions_required")

    def test_browser_apply_stops_when_response_button_missing(self):
        page = FakePage(text="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0434\u0438\u0437\u0430\u0439\u043d\u0435\u0440")

        result = apply_visible_page(page, vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))

        self.assertFalse(result.ok)
        self.assertEqual(result.error.value, "response_unavailable")

    def test_browser_apply_maps_navigation_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_browser_apply(
                vacancy=Vacancy(
                    id="bad",
                    name="Bad",
                    employer_name="Acme",
                    url="http://10.255.255.1/vacancy/bad",
                ),
                settings=UserSettings("resume-1", "Hello"),
                config=HhBrowserApplyConfig(
                    user_data_dir=str(Path(temp_dir) / "profile"),
                    headless=True,
                    timeout_ms=1,
                ),
            )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.type, "browser_error")


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
    def __init__(
        self,
        *,
        visible: bool,
        after_click_text: str = "",
        reveal_selector: str = "",
    ) -> None:
        self.visible = visible
        self.after_click_text = after_click_text
        self.reveal_selector = reveal_selector
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
        if self.reveal_selector and self.page is not None:
            self.page.selectors[self.reveal_selector].visible = True

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
