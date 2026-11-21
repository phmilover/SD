"""Хранилище build report: одна запись на сдачу, повторный анализ её перезаписывает."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .analyzer import BuildReport


class ReportRepository:
    def __init__(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = data_dir / "analysis.db"
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS reports (
                    submission_id TEXT PRIMARY KEY,
                    assignment_id TEXT NOT NULL,
                    body          TEXT NOT NULL
                )"""
            )

    def save(self, report: BuildReport) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO reports VALUES (?, ?, ?)",
                (report.submission_id, report.assignment_id, report.model_dump_json()),
            )

    def get(self, submission_id: str) -> BuildReport | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT body FROM reports WHERE submission_id = ?", (submission_id,)
            ).fetchone()
        return BuildReport.model_validate_json(row[0]) if row else None

    def list_by_assignment(self, assignment_id: str) -> list[BuildReport]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT body FROM reports WHERE assignment_id = ?", (assignment_id,)
            ).fetchall()
        reports = [BuildReport.model_validate_json(row[0]) for row in rows]
        return sorted(reports, key=lambda report: report.submitted_at)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self._db_path)
        try:
            with db:  # commit или rollback
                yield db
        finally:
            db.close()
