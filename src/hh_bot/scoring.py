from __future__ import annotations

from .models import ScoreResult, UserSettings, Vacancy


def evaluate_vacancy(
    vacancy: Vacancy,
    settings: UserSettings,
    *,
    already_applied: bool,
) -> ScoreResult:
    if already_applied or "got_response" in vacancy.relations:
        return ScoreResult(is_match=False, score=0, reason="already applied")

    text = _vacancy_text(vacancy)
    for keyword in settings.exclude_keywords:
        normalized = keyword.strip().lower()
        if normalized and normalized in text:
            return ScoreResult(
                is_match=False,
                score=0,
                reason=f"excluded keyword: {normalized}",
            )

    matched = [
        keyword.strip().lower()
        for keyword in settings.include_keywords
        if keyword.strip() and keyword.strip().lower() in text
    ]

    score = 40
    if settings.include_keywords:
        score = int((len(matched) / len(settings.include_keywords)) * 80)
    if settings.preferred_schedule and vacancy.schedule:
        if settings.preferred_schedule.lower() == vacancy.schedule.lower():
            score += 15
    score = min(score, 100)

    if matched:
        reason = f"matched keywords: {', '.join(matched)}"
    else:
        reason = "no include keywords configured"

    return ScoreResult(
        is_match=score >= settings.min_score,
        score=score,
        reason=reason,
    )


def _vacancy_text(vacancy: Vacancy) -> str:
    parts = [
        vacancy.name,
        vacancy.employer_name,
        vacancy.description,
        vacancy.salary or "",
        vacancy.area or "",
        vacancy.schedule or "",
        vacancy.employment or "",
    ]
    return " ".join(parts).lower()
