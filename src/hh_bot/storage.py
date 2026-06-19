from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .models import AuditEntry


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
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_resume_vacancy
                ON audit_entries (resume_id, vacancy_id)
                WHERE api_status IN ('sent', 'dry_run')
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
                  AND api_status IN ('sent', 'dry_run')
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

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn
