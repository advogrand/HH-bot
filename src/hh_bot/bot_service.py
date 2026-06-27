from __future__ import annotations

from dataclasses import replace

from .models import AuditEntry, Resume, UserSettings, Vacancy
from .scoring import evaluate_vacancy
from .storage import SQLiteStore
from .telegram_messages import render_candidate_message


class BotService:
    def __init__(
        self,
        *,
        store: SQLiteStore,
        settings: UserSettings,
        vacancies: list[Vacancy] | None = None,
        resumes: list[Resume] | None = None,
        oauth_start_url: str | None = None,
        oauth_state: str = "local-telegram-user",
        search_text: str = "",
        search_area: str | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.vacancies = vacancies or []
        self.resumes = resumes or []
        self.oauth_start_url = oauth_start_url
        self.oauth_state = oauth_state
        self.search_text = search_text
        self.search_area = search_area
        self.is_stopped = False

    def handle_command(self, command: str) -> str:
        name, _, arg = command.strip().partition(" ")
        if name == "/start":
            return self._start()
        if name == "/status":
            return self._status()
        if name == "/search":
            return self._search()
        if name == "/approve":
            return self._approve(arg.strip())
        if name == "/reject":
            return self._reject(arg.strip())
        if name == "/stop":
            return self._stop()
        if name == "/settings":
            return self._settings()
        if name == "/connect":
            return self._connect()
        if name == "/resumes":
            return self._resumes()
        if name == "/use_resume":
            return self._use_resume(arg.strip())
        if name == "/set_search":
            return self._set_search(arg.strip())
        if name == "/set_score":
            return self._set_score(arg.strip())
        if name == "/set_resume":
            return self._set_resume(arg.strip())
        if name == "/set_letter":
            return self._set_letter(arg.strip())
        if name == "/set_include":
            return self._set_include(arg.strip())
        if name == "/set_exclude":
            return self._set_exclude(arg.strip())
        return (
            "Unknown command. Use /start, /connect, /resumes, /use_resume, /status, "
            "/settings, /set_search, /set_score, /set_resume, /set_letter, "
            "/set_include, /set_exclude, /search, /approve, /reject, or /stop."
        )

    def _start(self) -> str:
        return (
            "HH Bot dry-run mode ready.\n"
            "Use /settings to review filters, /search to find candidates, and /status to inspect state."
        )

    def _settings(self) -> str:
        connected = "yes" if self.store.has_oauth_token(self.oauth_state) else "no"
        area = self.search_area or "any"
        return (
            f"hh.ru connected: {connected}\n"
            f"Resume: {self.settings.resume_id}\n"
            f"Minimum score: {self.settings.min_score}\n"
            f"Search text: {self.search_text or 'not set'}\n"
            f"Search area: {area}\n"
            f"Cover letter: {self.settings.cover_letter or 'not set'}\n"
            f"Include keywords: {', '.join(self.settings.include_keywords) or 'none'}\n"
            f"Exclude keywords: {', '.join(self.settings.exclude_keywords) or 'none'}"
        )

    def _connect(self) -> str:
        if not self.oauth_start_url:
            return "hh.ru OAuth is not configured yet. Set HH_CLIENT_ID, HH_CLIENT_SECRET, and HH_REDIRECT_URI."
        separator = "&" if "?" in self.oauth_start_url else "?"
        return f"Connect hh.ru: {self.oauth_start_url}{separator}state={self.oauth_state}"

    def _resumes(self) -> str:
        if not self.resumes:
            return "No resumes loaded. Connect hh.ru with /connect, then run /resumes again."
        lines = ["Available resumes:"]
        for resume in self.resumes:
            marker = " selected" if resume.id == self.settings.resume_id else ""
            lines.append(f"- {resume.title} ({resume.id}){marker}: /use_resume {resume.id}")
        return "\n".join(lines)

    def _use_resume(self, resume_id: str) -> str:
        for resume in self.resumes:
            if resume.id == resume_id:
                self.settings = replace(self.settings, resume_id=resume.id)
                self.store.save_selected_resume_id(resume.id)
                return f"Selected resume: {resume.title} ({resume.id})"
        return f"Resume {resume_id or '<empty>'} not found. Run /resumes first."

    def _set_search(self, search_text: str) -> str:
        if not search_text:
            return "Use /set_search followed by a vacancy search phrase."
        self.search_text = search_text
        self.store.save_search_text(search_text)
        return f"Search text updated: {search_text}"

    def _set_score(self, raw_score: str) -> str:
        try:
            min_score = int(raw_score)
        except ValueError:
            return "Use /set_score with a number from 0 to 100."
        if min_score < 0 or min_score > 100:
            return "Use /set_score with a number from 0 to 100."
        self.settings = replace(self.settings, min_score=min_score)
        self.store.save_min_score(min_score)
        return f"Minimum score updated: {min_score}"

    def _set_resume(self, resume_id: str) -> str:
        if not resume_id:
            return "Use /set_resume followed by a hh.ru resume id."
        self.settings = replace(self.settings, resume_id=resume_id)
        self.store.save_selected_resume_id(resume_id)
        return f"Resume updated: {resume_id}"

    def _set_letter(self, cover_letter: str) -> str:
        if not cover_letter:
            return "Use /set_letter followed by your exact cover letter text."
        self.settings = replace(self.settings, cover_letter=cover_letter)
        self.store.save_cover_letter(cover_letter)
        return "Cover letter updated."

    def _set_include(self, raw_keywords: str) -> str:
        keywords = _parse_keywords(raw_keywords)
        if not keywords:
            return "Use /set_include followed by comma-separated keywords."
        self.settings = replace(self.settings, include_keywords=keywords)
        self.store.save_include_keywords(keywords)
        return f"Include keywords updated: {', '.join(keywords)}"

    def _set_exclude(self, raw_keywords: str) -> str:
        keywords = _parse_keywords(raw_keywords)
        if not keywords:
            return "Use /set_exclude followed by comma-separated keywords."
        self.settings = replace(self.settings, exclude_keywords=keywords)
        self.store.save_exclude_keywords(keywords)
        return f"Exclude keywords updated: {', '.join(keywords)}"

    def _status(self) -> str:
        audit_count = len(self.store.list_audit_entries())
        stopped = "yes" if self.is_stopped else "no"
        return (
            "Mode: semi-automatic dry-run\n"
            f"Resume: {self.settings.resume_id}\n"
            f"Audit entries: {audit_count}\n"
            f"Stopped: {stopped}"
        )

    def _search(self) -> str:
        if self.is_stopped:
            return "Search is stopped. Restart the process before searching again."

        candidates: list[str] = []
        near_misses: list[tuple[int, str]] = []
        for vacancy in self.vacancies:
            already_applied = self.store.has_response(self.settings.resume_id, vacancy.id)
            score = evaluate_vacancy(vacancy, self.settings, already_applied=already_applied)
            if score.is_match:
                candidates.append(render_candidate_message(vacancy, score, self.settings))
            else:
                near_misses.append(
                    (
                        score.score,
                        "\n".join(
                            [
                                f"- {vacancy.name} ({score.score}/100)",
                                f"  Reason: {score.reason}",
                                f"  URL: {vacancy.url}",
                            ]
                        ),
                    )
                )

        if not candidates:
            if not self.vacancies:
                return "No vacancies loaded. Run /search or /browser_search first."
            near_misses.sort(key=lambda item: item[0], reverse=True)
            details = "\n".join(item[1] for item in near_misses[:5])
            return (
                f"Found {len(self.vacancies)} vacancies, but none passed filters.\n"
                f"Minimum score: {self.settings.min_score}\n"
                "Try /set_score 60 or adjust /set_search.\n\n"
                f"Top near misses:\n{details}"
            )
        return "\n\n---\n\n".join(candidates)

    def _approve(self, vacancy_id: str) -> str:
        vacancy = self._find_vacancy(vacancy_id)
        if not vacancy:
            return f"Vacancy {vacancy_id or '<empty>'} not found in current dry-run queue."

        already_applied = self.store.has_response(self.settings.resume_id, vacancy.id)
        score = evaluate_vacancy(vacancy, self.settings, already_applied=already_applied)
        if already_applied:
            return f"Vacancy {vacancy.id} already has a recorded response."

        self.store.record_audit(
            AuditEntry(
                vacancy_id=vacancy.id,
                vacancy_url=vacancy.url,
                vacancy_title=vacancy.name,
                employer_name=vacancy.employer_name,
                resume_id=self.settings.resume_id,
                score=score.score,
                reason=score.reason,
                cover_letter=self.settings.cover_letter,
                user_action="approved",
                api_status="dry_run",
            )
        )
        return f"Dry-run recorded for vacancy {vacancy.id}. No real hh.ru response was sent."

    def _reject(self, vacancy_id: str) -> str:
        vacancy = self._find_vacancy(vacancy_id)
        if not vacancy:
            return f"Vacancy {vacancy_id or '<empty>'} not found in current dry-run queue."
        self.store.record_audit(
            AuditEntry(
                vacancy_id=vacancy.id,
                vacancy_url=vacancy.url,
                vacancy_title=vacancy.name,
                employer_name=vacancy.employer_name,
                resume_id=self.settings.resume_id,
                score=0,
                reason="user rejected",
                cover_letter=self.settings.cover_letter,
                user_action="rejected",
                api_status="skipped",
            )
        )
        return f"Vacancy {vacancy.id} rejected and logged."

    def _stop(self) -> str:
        self.is_stopped = True
        return "Search and sending stopped. Auto mode is disabled."

    def _find_vacancy(self, vacancy_id: str) -> Vacancy | None:
        for vacancy in self.vacancies:
            if vacancy.id == vacancy_id:
                return vacancy
        return None


def _parse_keywords(raw_keywords: str) -> tuple[str, ...]:
    return tuple(part.strip().lower() for part in raw_keywords.split(",") if part.strip())
