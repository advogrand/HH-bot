from __future__ import annotations

from collections.abc import Callable

from .hh_apply import ApplyRequest, ApplyResult, HhApplyClient
from .models import AuditEntry, ScoreResult, UserSettings, Vacancy
from .storage import SQLiteStore


class HhApplyRunner:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        oauth_state: str,
        user_agent: str,
        real_apply_enabled: bool,
        apply_client_factory: Callable[..., HhApplyClient] = HhApplyClient,
    ) -> None:
        self.store = store
        self.oauth_state = oauth_state
        self.user_agent = user_agent
        self.real_apply_enabled = real_apply_enabled
        self.apply_client_factory = apply_client_factory

    async def approve(
        self,
        *,
        vacancy: Vacancy,
        settings: UserSettings,
        score: ScoreResult,
    ) -> ApplyResult:
        if not self.real_apply_enabled:
            self._record(
                vacancy=vacancy,
                settings=settings,
                score=score,
                api_status="dry_run",
            )
            return ApplyResult(
                ok=True,
                status="dry_run",
                user_message=f"Dry-run recorded for vacancy {vacancy.id}. No real hh.ru response was sent.",
            )

        token = self.store.get_oauth_token(self.oauth_state)
        if token is None:
            return ApplyResult(
                ok=False,
                status="not_connected",
                user_message="Connect hh.ru first with /connect, then approve again.",
            )

        client = self.apply_client_factory(
            access_token=token.access_token,
            user_agent=self.user_agent,
        )
        result = await client.apply_to_vacancy(
            ApplyRequest(
                resume_id=settings.resume_id,
                vacancy_id=vacancy.id,
                message=settings.cover_letter,
            )
        )
        self._record(
            vacancy=vacancy,
            settings=settings,
            score=score,
            api_status="sent" if result.ok else "failed",
            api_error_type=result.error.type if result.error else None,
            api_error_value=result.error.value if result.error else None,
        )
        return result

    def _record(
        self,
        *,
        vacancy: Vacancy,
        settings: UserSettings,
        score: ScoreResult,
        api_status: str,
        api_error_type: str | None = None,
        api_error_value: str | None = None,
    ) -> None:
        self.store.record_audit(
            AuditEntry(
                vacancy_id=vacancy.id,
                vacancy_url=vacancy.url,
                vacancy_title=vacancy.name,
                employer_name=vacancy.employer_name,
                resume_id=settings.resume_id,
                score=score.score,
                reason=score.reason,
                cover_letter=settings.cover_letter,
                user_action="approved",
                api_status=api_status,
                api_error_type=api_error_type,
                api_error_value=api_error_value,
            )
        )
