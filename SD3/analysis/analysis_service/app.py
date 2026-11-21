"""File Analysis (Build) Service: проверяет сдачу «на сборку», хранит и выдаёт отчёты."""

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .analyzer import Analyzer, BuildReport
from .repository import ReportRepository
from .settings import Settings
from .storage_client import StorageClient


class AnalyzeRequest(BaseModel):
    submission_id: str = Field(pattern=r"^[0-9a-f]{32}$")


def create_app(settings: Settings, storage_http: httpx.Client | None = None) -> FastAPI:
    storage = StorageClient(
        storage_http
        or httpx.Client(base_url=settings.storage_url, timeout=settings.http_timeout_seconds)
    )
    analyzer = Analyzer()
    repository = ReportRepository(settings.data_dir)
    app = FastAPI(
        title="ВышBuild · File Analysis Service",
        description="Проверка сдачи «на сборку», хранение и выдача build report.",
        version="1.0.0",
    )

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/reports", status_code=201, tags=["reports"])
    def analyze(request: AnalyzeRequest) -> BuildReport:
        submission, content = storage.fetch(request.submission_id)
        report = analyzer.analyze(submission, content)
        repository.save(report)
        return report

    @app.get("/reports", tags=["reports"])
    def list_reports(assignment_id: str) -> list[BuildReport]:
        return repository.list_by_assignment(assignment_id)

    @app.get("/reports/{submission_id}", tags=["reports"])
    def get_report(submission_id: str) -> BuildReport:
        report = repository.get(submission_id)
        if report is None:
            raise HTTPException(404, f"Отчёт по сдаче {submission_id} не найден")
        return report

    return app
