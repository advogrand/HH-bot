from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .models import AuditEntry
from .oauth import OAuthToken


class SQLiteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    vacancy_id TEXT NOT NULL,
                    vacancy_url TEXT NOT NULL,
                    vacancy_title TEXT NOT NULL,
                    employer_name TEXT NOT NULL,
                    resume_id TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    cover_letter TEXT NOT NULL,
                    user_action TEXT NOT NULL,
                    api_status TEXT NOT NULL,
                    api_error_type TEXT,
                    api_error_value TEXT
                )
                """
            )
            conn.execute("DROP INDEX IF EXISTS idx_audit_resume_vacancy")
            conn.execute(
                """
                CREATE UNIQUE INDEX idx_audit_resume_vacancy
                ON audit_entries (resume_id, vacancy_id)
                WHERE api_status = 'sent'
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    state TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_in INTEGER NOT NULL,
                    token_type TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def record_audit(self, entry: AuditEntry) -> None:
        timestamped = entry.with_timestamp()
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO audit_entries (
                    created_at,
                    vacancy_id,
                    vacancy_url,
                    vacancy_title,
                    employer_name,
                    resume_id,
                    score,
                    reason,
                    cover_letter,
                    user_action,
                    api_status,
                    api_error_type,
                    api_error_value
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamped.created_at,
                    timestamped.vacancy_id,
                    timestamped.vacancy_url,
                    timestamped.vacancy_title,
                    timestamped.employer_name,
                    timestamped.resume_id,
                    timestamped.score,
                    timestamped.reason,
                    timestamped.cover_letter,
                    timestamped.user_action,
                    timestamped.api_status,
                    timestamped.api_error_type,
                    timestamped.api_error_value,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def has_response(self, resume_id: str, vacancy_id: str) -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT 1
                FROM audit_entries
                WHERE resume_id = ?
                  AND vacancy_id = ?
                  AND api_status = 'sent'
                LIMIT 1
                """,
                (resume_id, vacancy_id),
            ).fetchone()
        finally:
            conn.close()
        return row is not None

    def list_audit_entries(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT
                    created_at,
                    vacancy_id,
                    vacancy_url,
                    vacancy_title,
                    employer_name,
                    resume_id,
                    score,
                    reason,
                    cover_letter,
                    user_action,
                    api_status,
                    api_error_type,
                    api_error_value
                FROM audit_entries
                ORDER BY id
                """
            ).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def count_responses_on_date(self, date_prefix: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM audit_entries
                WHERE created_at LIKE ?
                  AND api_status = 'sent'
                """,
                (f"{date_prefix}%",),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return 0
        return int(row["count"])

    def save_oauth_token(self, state: str, token: OAuthToken) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO oauth_tokens (
                    state,
                    access_token,
                    refresh_token,
                    expires_in,
                    token_type,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(state) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    expires_in = excluded.expires_in,
                    token_type = excluded.token_type,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    state,
                    token.access_token,
                    token.refresh_token,
                    token.expires_in,
                    token.token_type,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_oauth_token(self, state: str) -> OAuthToken | None:
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT access_token, refresh_token, expires_in, token_type
                FROM oauth_tokens
                WHERE state = ?
                """,
                (state,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return OAuthToken(
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            expires_in=row["expires_in"],
            token_type=row["token_type"],
        )

    def has_oauth_token(self, state: str) -> bool:
        return self.get_oauth_token(state) is not None

    def save_selected_resume_id(self, resume_id: str) -> None:
        self._set_setting("selected_resume_id", resume_id)

    def get_selected_resume_id(self) -> str | None:
        return self._get_setting("selected_resume_id")

    def save_search_text(self, search_text: str) -> None:
        self._set_setting("search_text", search_text)

    def get_search_text(self) -> str | None:
        return self._get_setting("search_text")

    def save_min_score(self, min_score: int) -> None:
        self._set_setting("min_score", str(min_score))

    def get_min_score(self) -> int | None:
        value = self._get_setting("min_score")
        if value is None:
            return None
        return int(value)

    def save_cover_letter(self, cover_letter: str) -> None:
        self._set_setting("cover_letter", cover_letter)

    def get_cover_letter(self) -> str | None:
        return self._get_setting("cover_letter")

    def save_include_keywords(self, keywords: tuple[str, ...]) -> None:
        self._set_setting("include_keywords", _join_keywords(keywords))

    def get_include_keywords(self) -> tuple[str, ...] | None:
        value = self._get_setting("include_keywords")
        if value is None:
            return None
        return _split_keywords(value)

    def save_exclude_keywords(self, keywords: tuple[str, ...]) -> None:
        self._set_setting("exclude_keywords", _join_keywords(keywords))

    def get_exclude_keywords(self) -> tuple[str, ...] | None:
        value = self._get_setting("exclude_keywords")
        if value is None:
            return None
        return _split_keywords(value)

    def _set_setting(self, key: str, value: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            conn.commit()
        finally:
            conn.close()

    def _get_setting(self, key: str) -> str | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?",
                (key,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return str(row["value"])

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn


def _join_keywords(keywords: tuple[str, ...]) -> str:
    return ",".join(keyword.strip() for keyword in keywords if keyword.strip())


def _split_keywords(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())
