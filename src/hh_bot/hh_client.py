from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .hh_errors import HhApiError, map_hh_error


@dataclass(frozen=True)
class HhResponse:
    ok: bool
    data: dict[str, Any] | None = None
    error: HhApiError | None = None


class HhClient:
    def __init__(self, *, access_token: str, user_agent: str) -> None:
        self.access_token = access_token
        self.user_agent = user_agent

    def authorization_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }

    @staticmethod
    def parse_error_response(status_code: int, payload: dict[str, Any]) -> HhResponse:
        errors = payload.get("errors")
        if not isinstance(errors, list):
            errors = []
        return HhResponse(ok=False, error=map_hh_error(status_code, errors))
