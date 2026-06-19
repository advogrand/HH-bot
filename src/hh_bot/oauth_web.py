from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse

from .oauth import HhOAuthClient, HhOAuthConfig
from .storage import SQLiteStore


def create_oauth_app(
    *,
    store: SQLiteStore,
    oauth_config: HhOAuthConfig | None = None,
    oauth_client: Any | None = None,
) -> FastAPI:
    if oauth_client is None:
        if oauth_config is None:
            raise ValueError("oauth_config or oauth_client is required")
        oauth_client = HhOAuthClient(oauth_config)

    app = FastAPI(title="HH Bot OAuth")

    @app.get("/oauth/hh/start")
    async def start(state: str) -> RedirectResponse:
        url = oauth_client.build_authorization_url(state=state)
        return RedirectResponse(url)

    @app.get("/oauth/hh/callback", response_class=PlainTextResponse)
    async def callback(code: str | None = None, state: str | None = None) -> str:
        if not code:
            raise HTTPException(status_code=400, detail="Missing OAuth code")
        if not state:
            raise HTTPException(status_code=400, detail="Missing OAuth state")
        token = await oauth_client.exchange_code(code)
        store.save_oauth_token(state, token)
        return "hh.ru account connected. You can return to Telegram."

    return app
