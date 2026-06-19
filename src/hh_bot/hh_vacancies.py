from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .hh_client import HhClient
from .models import Vacancy


@dataclass(frozen=True)
class SearchQuery:
    text: str
    area: str | None = None
    per_page: int = 20
    page: int = 0

    def to_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "text": self.text,
            "per_page": self.per_page,
            "page": self.page,
        }
        if self.area:
            params["area"] = self.area
        return params


class HhVacancySearchError(Exception):
    pass


class HhVacancyClient:
    def __init__(
        self,
        *,
        access_token: str | None,
        user_agent: str,
        http_client: Any | None = None,
        vacancies_url: str = "https://api.hh.ru/vacancies",
    ) -> None:
        self.access_token = access_token
        self.user_agent = user_agent
        self.http_client = http_client
        self.vacancies_url = vacancies_url

    async def search_vacancies(self, query: SearchQuery) -> list[Vacancy]:
        if self.http_client is not None:
            return await self._search_with_client(self.http_client, query)

        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            return await self._search_with_client(client, query)

    async def _search_with_client(self, client: Any, query: SearchQuery) -> list[Vacancy]:
        headers = {"User-Agent": self.user_agent}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        response = await client.get(
            self.vacancies_url,
            headers=headers,
            params=query.to_params(),
        )
        payload = response.json()
        if response.status_code >= 400:
            error = HhClient.parse_error_response(response.status_code, payload).error
            message = error.user_message if error is not None else "hh.ru vacancy search failed."
            raise HhVacancySearchError(message)
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        return [map_vacancy(item) for item in items if isinstance(item, dict)]


def map_vacancy(raw: dict[str, Any]) -> Vacancy:
    salary = _format_salary(raw.get("salary"))
    employer = raw.get("employer") if isinstance(raw.get("employer"), dict) else {}
    area = raw.get("area") if isinstance(raw.get("area"), dict) else {}
    schedule = raw.get("schedule") if isinstance(raw.get("schedule"), dict) else {}
    employment = raw.get("employment") if isinstance(raw.get("employment"), dict) else {}
    relations = raw.get("relations")
    if not isinstance(relations, list):
        relations = []

    return Vacancy(
        id=str(raw.get("id") or ""),
        name=str(raw.get("name") or ""),
        employer_name=str(employer.get("name") or ""),
        url=str(raw.get("alternate_url") or raw.get("url") or ""),
        description=_description_from_snippet(raw.get("snippet")),
        salary=salary,
        area=_optional_str(area.get("name")),
        schedule=_optional_str(schedule.get("id") or schedule.get("name")),
        employment=_optional_str(employment.get("id") or employment.get("name")),
        relations=tuple(str(relation) for relation in relations),
    )


def _description_from_snippet(snippet: Any) -> str:
    if not isinstance(snippet, dict):
        return ""
    parts = [snippet.get("requirement"), snippet.get("responsibility")]
    return " ".join(str(part) for part in parts if part)


def _format_salary(salary: Any) -> str | None:
    if not isinstance(salary, dict):
        return None
    currency = salary.get("currency")
    salary_from = salary.get("from")
    salary_to = salary.get("to")
    if salary_from and salary_to:
        return f"{salary_from}-{salary_to} {currency}".strip()
    if salary_from:
        return f"from {salary_from} {currency}".strip()
    if salary_to:
        return f"to {salary_to} {currency}".strip()
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
