"""Сводка по заданию: сдачи из хранилища, соединённые с отчётами анализа."""

from .schemas import AssignmentSummary, BuildReport, Submission, SubmissionRow


def build_summary(
    assignment_id: str, submissions: list[Submission], reports: list[BuildReport]
) -> AssignmentSummary:
    reports_by_id = {report.submission_id: report for report in reports}
    ordered = sorted(submissions, key=lambda submission: submission.submitted_at)
    latest = {submission.student: submission.submission_id for submission in ordered}
    rows = [
        SubmissionRow(
            submission=submission,
            report=reports_by_id.get(submission.submission_id),
            is_latest=latest[submission.student] == submission.submission_id,
        )
        for submission in ordered
    ]
    current = [row for row in rows if row.is_latest]
    return AssignmentSummary(
        assignment_id=assignment_id,
        students=len(current),
        passed=sum(1 for row in current if row.report and row.report.success),
        failed=sum(1 for row in current if row.report and not row.report.success),
        not_analyzed=sum(1 for row in current if row.report is None),
        submissions=rows,
    )
