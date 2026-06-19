from __future__ import annotations

from collections.abc import Callable

from .hh_vacancies import HhVacancyClient, SearchQuery
from .models import Vacancy
from .storage import SQLiteStore


class HhSearchRunner:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        oauth_state: str,
        user_agent: str,
        search_text: str,
        area: str | None = None,
        per_page: int = 20,
        vacancy_client_factory: Callable[..., HhVacancyClient] = HhVacancyClient,
    ) -> None:
        self.store = store
        self.oauth_state = oauth_state
        self.user_agent = user_agent
        self.search_text = search_text
        self.area = area
        self.per_page = per_page
        self.vacancy_client_factory = vacancy_client_factory

    async def fetch_vacancies(self) -> list[Vacancy]:
        token = self.store.get_oauth_token(self.oauth_state)
        if token is None:
            return []
        client = self.vacancy_client_factory(
            access_token=token.access_token,
            user_agent=self.user_agent,
        )
        return await client.search_vacancies(
            SearchQuery(
                text=self.search_text,
                area=self.area,
                per_page=self.per_page,
            )
        )
