from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HhApiError:
    status_code: int
    type: str
    value: str
    user_message: str
    fallback_url: str | None = None


_KNOWN_MESSAGES = {
    "already_applied": "This resume already has a response for this vacancy.",
    "test_required": "This vacancy requires a test. API response is unavailable.",
    "limit_exceeded": "hh.ru response limit reached. Sending is paused.",
    "captcha_required": "hh.ru requires captcha. Use the official fallback URL.",
    "token_expired": "hh.ru token expired. Reconnect or refresh authorization.",
    "token_revoked": "hh.ru token was revoked. Reconnect account.",
    "bad_authorization": "hh.ru authorization failed. Reconnect account.",
    "forbidden": "hh.ru API denied vacancy search. Connect hh.ru with /connect after the app is approved.",
    "resume_not_found": "Resume is hidden, deleted, or unavailable.",
    "resume_deleted": "Resume is deleted or hidden.",
    "invalid_vacancy": "Vacancy is archived, hidden, or unavailable.",
    "too_long_message": "Cover letter is too long. Shorten it before sending.",
    "empty_message": "Cover letter is empty, but hh.ru requires message text.",
}


def map_hh_error(status_code: int, errors: list[dict[str, Any]]) -> HhApiError:
    first = errors[0] if errors else {}
    error_type = str(first.get("type") or "unknown")
    value = str(first.get("value") or error_type)
    fallback_url = first.get("fallback_url")
    message = _KNOWN_MESSAGES.get(value) or _KNOWN_MESSAGES.get(error_type)
    if not message:
        message = f"hh.ru API error: {error_type}/{value} ({status_code})."
    return HhApiError(
        status_code=status_code,
        type=error_type,
        value=value,
        user_message=message,
        fallback_url=str(fallback_url) if fallback_url else None,
    )
