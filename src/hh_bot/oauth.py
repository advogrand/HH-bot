from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode


@dataclass(frozen=True)
class HhOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    user_agent: str
    authorize_url: str = "https://hh.ru/oauth/authorize"
    token_url: str = "https://api.hh.ru/token"
    me_url: str = "https://api.hh.ru/me"


@dataclass(frozen=True)
class OAuthToken:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


class HhOAuthClient:
    def __init__(self, config: HhOAuthConfig, http_client: Any | None = None) -> None:
        self.config = config
        self._http_client = http_client

    def build_authorization_url(self, *, state: str, force_login: bool = False) -> str:
        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }
        if force_login:
            params["force_login"] = "true"
        return f"{self.config.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> OAuthToken:
        return await self._post_token(
            {
                "grant_type": "authorization_code",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "code": code,
                "redirect_uri": self.config.redirect_uri,
            }
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthToken:
        return await self._post_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
        )

    async def get_me(self, access_token: str) -> dict[str, Any]:
        client = self._require_http_client()
        response = await client.get(
            self.config.me_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": self.config.user_agent,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("hh.ru /me response must be an object")
        return payload

    async def _post_token(self, data: dict[str, str]) -> OAuthToken:
        client = self._require_http_client()
        response = await client.post(self.config.token_url, data=data)
        response.raise_for_status()
        payload = response.json()
        return _token_from_payload(payload)

    def _require_http_client(self) -> Any:
        if self._http_client is None:
            import httpx

            self._http_client = httpx.AsyncClient(timeout=20)
        return self._http_client


def _token_from_payload(payload: dict[str, Any]) -> OAuthToken:
    try:
        access_token = str(payload["access_token"])
        refresh_token = str(payload["refresh_token"])
        expires_in = int(payload["expires_in"])
        token_type = str(payload["token_type"])
    except KeyError as exc:
        raise ValueError(f"hh.ru token response missing {exc.args[0]}") from exc
    return OAuthToken(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        token_type=token_type,
    )
