from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Vacancy:
    id: str
    name: str
    employer_name: str
    url: str
    description: str = ""
    salary: str | None = None
    area: str | None = None
    schedule: str | None = None
    employment: str | None = None
    relations: tuple[str, ...] = ()


@dataclass(frozen=True)
class UserSettings:
    resume_id: str
    cover_letter: str
    include_keywords: tuple[str, ...] = ()
    exclude_keywords: tuple[str, ...] = ()
    preferred_schedule: str | None = None
    min_score: int = 60


@dataclass(frozen=True)
class ScoreResult:
    is_match: bool
    score: int
    reason: str


@dataclass(frozen=True)
class AuditEntry:
    vacancy_id: str
    vacancy_url: str
    vacancy_title: str
    employer_name: str
    resume_id: str
    score: int
    reason: str
    cover_letter: str
    user_action: str
    api_status: str
    api_error_type: str | None = None
    api_error_value: str | None = None
    created_at: str = ""

    def with_timestamp(self) -> "AuditEntry":
        if self.created_at:
            return self
        return AuditEntry(
            vacancy_id=self.vacancy_id,
            vacancy_url=self.vacancy_url,
            vacancy_title=self.vacancy_title,
            employer_name=self.employer_name,
            resume_id=self.resume_id,
            score=self.score,
            reason=self.reason,
            cover_letter=self.cover_letter,
            user_action=self.user_action,
            api_status=self.api_status,
            api_error_type=self.api_error_type,
            api_error_value=self.api_error_value,
            created_at=datetime.now(UTC).isoformat(),
        )
