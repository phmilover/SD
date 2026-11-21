"""Контракт публичного API. Повторяет ответы сервисов: у gateway нет общего кода с ними."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Submission(BaseModel):
    submission_id: str
    student: str
    assignment_id: str
    submitted_at: datetime
    filename: str
    size_bytes: int
    sha256: str


class CheckResult(BaseModel):
    name: str
    title: str
    status: Literal["passed", "failed", "warning", "skipped"]
    message: str


class BuildReport(BaseModel):
    submission_id: str
    student: str
    assignment_id: str
    submitted_at: datetime
    filename: str
    status: Literal["SUCCESS", "FAILED"]
    success: bool
    language: str | None
    checks: list[CheckResult]
    analyzed_at: datetime


class ServiceError(BaseModel):
    error: str
    service: str
    message: str


class SubmissionResult(BaseModel):
    """Итог сдачи. `report` пуст, если анализ не удался: тогда в `analysis_error` причина."""

    submission: Submission
    report: BuildReport | None
    analysis_error: ServiceError | None = None


class SubmissionRow(BaseModel):
    submission: Submission
    report: BuildReport | None
    is_latest: bool  # последняя попытка этого студента по заданию


class AssignmentSummary(BaseModel):
    """Сводка по заданию. Счётчики считаются по последней попытке каждого студента."""

    assignment_id: str
    students: int
    passed: int
    failed: int
    not_analyzed: int
    submissions: list[SubmissionRow]
