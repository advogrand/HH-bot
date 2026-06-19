from __future__ import annotations

from .models import ScoreResult, UserSettings, Vacancy


def render_candidate_message(
    vacancy: Vacancy,
    score: ScoreResult,
    settings: UserSettings,
) -> str:
    details = [
        f"Vacancy: {vacancy.name}",
        f"Company: {vacancy.employer_name}",
        f"Score: {score.score}/100",
        f"Reason: {score.reason}",
        f"URL: {vacancy.url}",
    ]
    if vacancy.salary:
        details.append(f"Salary: {vacancy.salary}")
    if vacancy.area:
        details.append(f"Area: {vacancy.area}")
    if vacancy.schedule:
        details.append(f"Schedule: {vacancy.schedule}")
    if vacancy.employment:
        details.append(f"Employment: {vacancy.employment}")

    details.extend(
        [
            "",
            "Cover letter:",
            settings.cover_letter,
            "",
            f"Approve: /approve {vacancy.id}",
            f"Reject: /reject {vacancy.id}",
        ]
    )
    return "\n".join(details)
