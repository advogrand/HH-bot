from __future__ import annotations

from typing import Any

from .models import Resume


class HhResumeError(Exception):
    pass


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
        payload = response.json()
        if response.status_code >= 400:
            raise HhResumeError(_resume_error_message(response.status_code, payload))
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


def _resume_error_message(status_code: int, payload: dict[str, Any]) -> str:
    errors = payload.get("errors")
    first = errors[0] if isinstance(errors, list) and errors else {}
    error_type = str(first.get("type") or "unknown")
    value = str(first.get("value") or error_type)
    if status_code == 403 or error_type == "forbidden":
        return "hh.ru denied resume list access. Use /set_resume with a direct resume id."
    if value == "bad_user_agent":
        return "hh.ru rejected User-Agent. Update HH_USER_AGENT and retry."
    return f"hh.ru resume API error: {error_type}/{value} ({status_code})."
