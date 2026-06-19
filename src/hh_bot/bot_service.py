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
        return (
            "Unknown command. Use /start, /connect, /resumes, /use_resume, /status, "
            "/settings, /search, /approve, /reject, or /stop."
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
        for vacancy in self.vacancies:
            already_applied = self.store.has_response(self.settings.resume_id, vacancy.id)
            score = evaluate_vacancy(vacancy, self.settings, already_applied=already_applied)
            if score.is_match:
                candidates.append(render_candidate_message(vacancy, score, self.settings))

        if not candidates:
            return "No matching vacancies found in dry-run source."
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
