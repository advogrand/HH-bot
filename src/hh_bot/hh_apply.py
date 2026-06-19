from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .hh_errors import HhApiError, map_hh_error


@dataclass(frozen=True)
class ApplyRequest:
    resume_id: str
    vacancy_id: str
    message: str


@dataclass(frozen=True)
class ApplyResult:
    ok: bool
    status: str
    error: HhApiError | None = None
    user_message: str = ""


class HhApplyClient:
    def __init__(
        self,
        *,
        access_token: str,
        user_agent: str,
        http_client: Any | None = None,
        apply_url: str = "https://api.hh.ru/negotiations",
    ) -> None:
        self.access_token = access_token
        self.user_agent = user_agent
        self.http_client = http_client
        self.apply_url = apply_url

    async def apply_to_vacancy(self, request: ApplyRequest) -> ApplyResult:
        if self.http_client is not None:
            return await self._apply_with_client(self.http_client, request)

        import httpx

        async with httpx.AsyncClient(timeout=20) as client:
            return await self._apply_with_client(client, request)

    async def _apply_with_client(self, client: Any, request: ApplyRequest) -> ApplyResult:
        response = await client.post(
            self.apply_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent,
            },
            data={
                "resume_id": request.resume_id,
                "vacancy_id": request.vacancy_id,
                "message": request.message,
            },
        )
        if response.status_code == 201:
            return ApplyResult(ok=True, status="sent", user_message="Real hh.ru response sent.")

        payload = response.json()
        errors = payload.get("errors")
        if not isinstance(errors, list):
            errors = []
        error = map_hh_error(response.status_code, errors)
        return ApplyResult(
            ok=False,
            status="failed",
            error=error,
            user_message=error.user_message,
        )
