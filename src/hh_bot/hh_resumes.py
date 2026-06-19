from __future__ import annotations

from typing import Any

from .models import Resume


class HhResumeClient:
    def __init__(
        self,
        *,
        access_token: str,
        user_agent: str,
        http_client: Any | None = None,
        resumes_url: str = "https://api.hh.ru/resumes/mine",
    ) -> None:
        self.access_token = access_token
        self.user_agent = user_agent
        self.http_client = http_client
        self.resumes_url = resumes_url

    async def list_mine(self) -> list[Resume]:
        if self.http_client is not None:
            return await self._list_with_client(self.http_client)

        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            return await self._list_with_client(client)

    async def _list_with_client(self, client: Any) -> list[Resume]:
        response = await client.get(
            self.resumes_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent,
            },
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items", [])
        if not isinstance(items, list):
            return []
        return [map_resume(item) for item in items if isinstance(item, dict)]


def map_resume(raw: dict[str, Any]) -> Resume:
    return Resume(
        id=str(raw.get("id") or ""),
        title=str(raw.get("title") or raw.get("name") or ""),
        url=str(raw.get("url") or ""),
    )
