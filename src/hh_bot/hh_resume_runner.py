from __future__ import annotations

from collections.abc import Callable

from .hh_resumes import HhResumeClient
from .models import Resume
from .storage import SQLiteStore


class HhResumeRunner:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        oauth_state: str,
        user_agent: str,
        resume_client_factory: Callable[..., HhResumeClient] = HhResumeClient,
    ) -> None:
        self.store = store
        self.oauth_state = oauth_state
        self.user_agent = user_agent
        self.resume_client_factory = resume_client_factory

    async def fetch_resumes(self) -> list[Resume]:
        token = self.store.get_oauth_token(self.oauth_state)
        if token is None:
            return []
        client = self.resume_client_factory(
            access_token=token.access_token,
            user_agent=self.user_agent,
        )
        return await client.list_mine()
