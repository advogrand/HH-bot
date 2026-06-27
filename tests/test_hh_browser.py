import unittest

from hh_bot.hh_browser import collect_vacancies_for_review


class HhBrowserTests(unittest.TestCase):
    def test_collect_vacancies_for_review_maps_visible_cards(self):
        page = FakePage(
            [
                {
                    "id": "123",
                    "title": "Python Developer",
                    "url": "https://hh.ru/vacancy/123",
                    "employer": "Acme",
                    "requirement": "Python, FastAPI",
                    "responsibility": "Build backend services",
                    "area": "Moscow",
                    "apply": True,
                },
                {
                    "id": "456",
                    "title": "PHP Developer",
                    "url": "https://hh.ru/vacancy/456",
                    "employer": "Legacy LLC",
                    "requirement": "PHP",
                    "responsibility": "Support legacy app",
                    "area": "Remote",
                    "apply": False,
                },
            ]
        )

        vacancies = collect_vacancies_for_review(page, limit=10)

        self.assertEqual(len(vacancies), 2)
        self.assertEqual(vacancies[0].id, "123")
        self.assertEqual(vacancies[0].name, "Python Developer")
        self.assertEqual(vacancies[0].employer_name, "Acme")
        self.assertEqual(vacancies[0].area, "Moscow")
        self.assertEqual(vacancies[0].relations, ("browser_apply_available",))
        self.assertIn("FastAPI", vacancies[0].description)
        self.assertEqual(vacancies[1].relations, ())

    def test_collect_vacancies_for_review_respects_limit(self):
        page = FakePage(
            [
                {
                    "id": str(i),
                    "title": f"Python Developer {i}",
                    "url": f"https://hh.ru/vacancy/{i}",
                }
                for i in range(3)
            ]
        )

        vacancies = collect_vacancies_for_review(page, limit=2)

        self.assertEqual([vacancy.id for vacancy in vacancies], ["0", "1"])


class FakePage:
    def __init__(self, cards):
        self.cards = cards

    def locator(self, selector):
        if selector == '[data-qa="vacancy-serp__vacancy"]':
            return FakeListLocator([FakeCard(card) for card in self.cards])
        return FakeListLocator([])


class FakeListLocator:
    def __init__(self, items):
        self.items = items
        self.first = items[0] if items else FakeValueLocator(None)

    def count(self):
        return len(self.items)

    def nth(self, index):
        return self.items[index]


class FakeCard:
    def __init__(self, data):
        self.data = data

    def locator(self, selector):
        values = {
            '[data-qa="serp-item__title-text"]': self.data.get("title"),
            'a[data-qa="serp-item__title"]': self.data.get("title"),
            '[data-qa="vacancy-serp__vacancy-employer-text"]': self.data.get("employer"),
            '[data-qa="vacancy-serp__vacancy_snippet_requirement"]': self.data.get("requirement"),
            '[data-qa="vacancy-serp__vacancy_snippet_responsibility"]': self.data.get("responsibility"),
            '[data-qa="vacancy-serp__vacancy-address"]': self.data.get("area"),
            '[data-qa="vacancy-serp__vacancy_response"]': "Откликнуться"
            if self.data.get("apply")
            else None,
        }
        if selector == 'a[data-qa="serp-item__title"]':
            return FakeListLocator([FakeValueLocator(values[selector], href=self.data.get("url"))])
        value = values.get(selector)
        return FakeListLocator([FakeValueLocator(value)] if value else [])

    def inner_text(self):
        return " ".join(str(value) for value in self.data.values() if value)


class FakeValueLocator:
    def __init__(self, text, *, href=None):
        self.text = text
        self.href = href
        self.first = self

    def count(self):
        return 1 if self.text is not None or self.href is not None else 0

    def inner_text(self):
        return self.text or ""

    def get_attribute(self, name):
        if name == "href":
            return self.href
        return None


if __name__ == "__main__":
    unittest.main()
