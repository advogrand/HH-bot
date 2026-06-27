from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Awaitable, Callable

from .models import UserSettings, Vacancy
from .scoring import evaluate_vacancy
from .storage import SQLiteStore


REMOTE_MARKERS = (
    "удален",
    "удалён",
    "remote",
    "дистанц",
    "из дома",
)


@dataclass(frozen=True)
class AutoApplySummary:
    sent: int = 0
    failed: int = 0
    skipped_non_remote: int = 0
    skipped_score: int = 0
    skipped_duplicate: int = 0
    skipped_limit: int = 0
    user_message: str = ""


class AutoApplyRunner:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        apply_runner,
        daily_limit: int = 25,
        delay_seconds: int = 30,
        remote_only: bool = True,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.store = store
        self.apply_runner = apply_runner
        self.daily_limit = daily_limit
        self.delay_seconds = delay_seconds
        self.remote_only = remote_only
        self.sleep = sleep

    async def run(
        self,
        *,
        vacancies: list[Vacancy],
        settings: UserSettings,
        confirm: bool,
    ) -> AutoApplySummary:
        if not confirm:
            mode = "real" if self._real_apply_enabled() else "dry-run"
            return AutoApplySummary(
                user_message=(
                    "Auto apply preview only. Use /auto_apply confirm to start. "
                    f"Mode: {mode}. "
                    f"Rules: remote_only={self.remote_only}, delay={self.delay_seconds}s, "
                    f"daily_limit={self.daily_limit}."
                )
            )

        remaining = max(0, self.daily_limit - self.store.count_responses_on_date(_today()))
        sent = failed = skipped_non_remote = skipped_score = skipped_duplicate = skipped_limit = 0

        for vacancy in vacancies:
            if self.remote_only and not is_remote_vacancy(vacancy):
                skipped_non_remote += 1
                continue
            if self.store.has_response(settings.resume_id, vacancy.id):
                skipped_duplicate += 1
                continue

            score = evaluate_vacancy(vacancy, settings, already_applied=False)
            if not score.is_match:
                skipped_score += 1
                continue
            if sent >= remaining:
                skipped_limit += 1
                continue

            if sent > 0 and self.delay_seconds > 0 and self._real_apply_enabled():
                await self.sleep(self.delay_seconds)
            result = await self.apply_runner.approve(
                vacancy=vacancy,
                settings=settings,
                score=score,
            )
            if result.ok:
                sent += 1
            else:
                failed += 1

        return AutoApplySummary(
            sent=sent,
            failed=failed,
            skipped_non_remote=skipped_non_remote,
            skipped_score=skipped_score,
            skipped_duplicate=skipped_duplicate,
            skipped_limit=skipped_limit,
            user_message=(
                "Auto apply finished.\n"
                f"Sent: {sent}\n"
                f"Failed: {failed}\n"
                f"Skipped non-remote: {skipped_non_remote}\n"
                f"Skipped score: {skipped_score}\n"
                f"Skipped duplicate: {skipped_duplicate}\n"
                f"Skipped daily limit: {skipped_limit}"
            ),
        )

    def _real_apply_enabled(self) -> bool:
        return bool(getattr(self.apply_runner, "real_apply_enabled", True))


def is_remote_vacancy(vacancy: Vacancy) -> bool:
    text = " ".join(
        [
            vacancy.name,
            vacancy.employer_name,
            vacancy.description,
            vacancy.area or "",
            vacancy.schedule or "",
            vacancy.employment or "",
        ]
    ).lower()
    return any(marker in text for marker in REMOTE_MARKERS)


def _today() -> str:
    return datetime.now(UTC).date().isoformat()
