"""Сдачи и их файлы: метаданные в SQLite, содержимое — файлами на диске."""

import hashlib
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


class Submission(BaseModel):
    submission_id: str
    student: str
    assignment_id: str
    submitted_at: datetime
    filename: str
    size_bytes: int
    sha256: str


class SubmissionRepository:
    def __init__(self, data_dir: Path) -> None:
        self._files_dir = data_dir / "files"
        self._files_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = data_dir / "storage.db"
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS submissions (
                    submission_id TEXT PRIMARY KEY,
                    student       TEXT NOT NULL,
                    assignment_id TEXT NOT NULL,
                    submitted_at  TEXT NOT NULL,
                    filename      TEXT NOT NULL,
                    size_bytes    INTEGER NOT NULL,
                    sha256        TEXT NOT NULL
                )"""
            )

    def add(self, student: str, assignment_id: str, filename: str, content: bytes) -> Submission:
        submission = Submission(
            submission_id=uuid.uuid4().hex,
            student=student,
            assignment_id=assignment_id,
            submitted_at=datetime.now(UTC),
            filename=filename,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )
        # Сначала файл, потом строка в БД: запись без файла хуже, чем файл без записи.
        self.file_path(submission.submission_id).write_bytes(content)
        with self._connect() as db:
            db.execute(
                "INSERT INTO submissions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    submission.submission_id,
                    submission.student,
                    submission.assignment_id,
                    submission.submitted_at.isoformat(),
                    submission.filename,
                    submission.size_bytes,
                    submission.sha256,
                ),
            )
        return submission

    def get(self, submission_id: str) -> Submission | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM submissions WHERE submission_id = ?", (submission_id,)
            ).fetchone()
        return Submission(**row) if row else None

    def list_by_assignment(self, assignment_id: str) -> list[Submission]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM submissions WHERE assignment_id = ? ORDER BY submitted_at",
                (assignment_id,),
            ).fetchall()
        return [Submission(**row) for row in rows]

    def file_path(self, submission_id: str) -> Path:
        return self._files_dir / submission_id

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        try:
            with db:  # commit или rollback
                yield db
        finally:
            db.close()
