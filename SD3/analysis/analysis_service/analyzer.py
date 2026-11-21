"""Прогон проверок над сдачей и сборка build report."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from .checks import DEFAULT_CHECKS, Check, CheckResult, detect_language
from .project import Project


class SubmissionInfo(BaseModel):
    """Те поля сдачи из File Storing Service, которые нужны отчёту."""

    submission_id: str
    student: str
    assignment_id: str
    submitted_at: datetime
    filename: str


class BuildReport(SubmissionInfo):
    status: Literal["SUCCESS", "FAILED"]
    success: bool
    language: str | None
    checks: list[CheckResult]
    analyzed_at: datetime


class Analyzer:
    def __init__(self, checks: Sequence[Check] = DEFAULT_CHECKS) -> None:
        self._checks = checks

    def analyze(self, submission: SubmissionInfo, content: bytes) -> BuildReport:
        project = Project.load(submission.filename, content)
        results: list[CheckResult] = []
        blocked = False
        for check in self._checks:
            if blocked:
                results.append(
                    CheckResult(
                        name=check.name,
                        title=check.title,
                        status="skipped",
                        message="Не проверялось: провалена обязательная проверка выше",
                    )
                )
                continue
            result = check(project)
            results.append(result)
            blocked = check.blocking and result.status == "failed"

        success = all(result.status != "failed" for result in results)
        return BuildReport(
            **submission.model_dump(),
            status="SUCCESS" if success else "FAILED",
            success=success,
            language=detect_language(project),
            checks=results,
            analyzed_at=datetime.now(UTC),
        )
