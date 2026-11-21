"""API Gateway: единая точка входа. Маршрутизирует запросы и оркеструет «сохранить → проверить»."""

from pathlib import Path as FsPath
from typing import Annotated

import httpx
from fastapi import FastAPI, File, Form, Path, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from .clients import AnalysisClient, StorageClient, UpstreamError
from .schemas import AssignmentSummary, BuildReport, ServiceError, SubmissionResult
from .settings import Settings
from .summary import build_summary

# Идентификаторы попадают в URL внутренних сервисов, поэтому формат проверяется на входе.
ASSIGNMENT_ID_PATTERN = r"^[\w.-]{1,50}$"
SubmissionId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$", description="id сдачи")]
AssignmentId = Annotated[str, Path(pattern=ASSIGNMENT_ID_PATTERN, examples=["dz-3"])]

ERRORS = {
    404: {"model": ServiceError, "description": "Сдача или отчёт не найдены"},
    422: {"model": ServiceError, "description": "Некорректный запрос"},
    502: {"model": ServiceError, "description": "Сервис ответил ошибкой"},
    503: {"model": ServiceError, "description": "Сервис недоступен"},
    504: {"model": ServiceError, "description": "Сервис не ответил вовремя"},
}
UPLOAD_ERRORS = {
    411: {"model": ServiceError, "description": "Нет заголовка Content-Length"},
    413: {"model": ServiceError, "description": "Файл слишком большой"},
}
FORM_OVERHEAD_BYTES = 64 * 1024  # поля формы и границы multipart сверх самого файла

templates = Jinja2Templates(directory=FsPath(__file__).parent / "templates")


def error_response(request: Request, status_code: int, body: ServiceError) -> Response:
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse(
            request, "error.html", {"error": body}, status_code=status_code
        )
    return JSONResponse(body.model_dump(), status_code=status_code)


def create_app(
    settings: Settings,
    storage_http: httpx.Client | None = None,
    analysis_http: httpx.Client | None = None,
) -> FastAPI:
    def http(url: str) -> httpx.Client:
        return httpx.Client(base_url=url, timeout=settings.http_timeout_seconds)

    storage = StorageClient(storage_http or http(settings.storage_url))
    analysis = AnalysisClient(analysis_http or http(settings.analysis_url))

    app = FastAPI(
        title="ВышBuild · API Gateway",
        description=(
            "Приём сдач домашних работ и проверка «на сборку». "
            "«Если зелёное — можно спать».\n\n"
            "Сценарий сдачи: Gateway → File Storing Service (сохранить) → "
            "File Analysis Service (проверить) → ответ клиенту."
        ),
        version="1.0.0",
    )

    def gateway_error(error: str, message: str) -> ServiceError:
        return ServiceError(error=error, service="API Gateway", message=message)

    @app.exception_handler(UpstreamError)
    def upstream_error(request: Request, error: UpstreamError) -> Response:
        return error_response(request, error.status_code, error.body)

    @app.exception_handler(RequestValidationError)
    def validation_error(request: Request, error: RequestValidationError) -> Response:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'][1:])}: {item['msg']}"
            for item in error.errors()
        )
        return error_response(request, 422, gateway_error("bad_request", problems))

    @app.middleware("http")
    async def limit_upload_size(request: Request, call_next):
        # Отказываем до разбора multipart, чтобы большой файл не попал даже во временный файл.
        if request.method == "POST" and request.url.path == "/submissions":
            length = request.headers.get("content-length")
            if length is None or not length.isdigit():
                body = gateway_error("length_required", "Нужен заголовок Content-Length")
                return error_response(request, 411, body)
            if int(length) > settings.max_upload_bytes + FORM_OVERHEAD_BYTES:
                limit_mb = settings.max_upload_bytes // 2**20
                body = gateway_error("too_large", f"Файл больше {limit_mb} МБ")
                return error_response(request, 413, body)
        return await call_next(request)

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse("/docs")

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        def state(client: StorageClient | AnalysisClient) -> str:
            return "ok" if client.is_alive() else "unavailable"

        return {"gateway": "ok", "storage": state(storage), "analysis": state(analysis)}

    @app.post(
        "/submissions",
        status_code=201,
        tags=["student"],
        summary="Сдать работу: сохранить файл и сразу проверить",
        responses={
            202: {"model": SubmissionResult, "description": "Сохранено, но анализ не удался"},
            **ERRORS,
            **UPLOAD_ERRORS,
        },
    )
    def submit(
        student: Annotated[str, Form(description="Кто сдаёт", examples=["Иванов Иван"])],
        assignment_id: Annotated[
            str, Form(description="Задание", examples=["dz-3"], pattern=ASSIGNMENT_ID_PATTERN)
        ],
        file: Annotated[UploadFile, File(description="Исходники: .zip или один файл")],
        response: Response,
    ) -> SubmissionResult:
        submission = storage.upload(student, assignment_id, file.filename or "upload", file.file)
        try:
            report = analysis.analyze(submission.submission_id)
        except UpstreamError as error:
            # Работа уже сохранена: не теряем её, а сообщаем, что отчёт можно получить позже.
            response.status_code = 202
            return SubmissionResult(submission=submission, report=None, analysis_error=error.body)
        return SubmissionResult(submission=submission, report=report)

    @app.get("/submissions/{submission_id}", tags=["student"], responses=ERRORS)
    def get_submission(submission_id: SubmissionId) -> SubmissionResult:
        submission = storage.get(submission_id)
        try:
            return SubmissionResult(submission=submission, report=analysis.find(submission_id))
        except UpstreamError as error:
            return SubmissionResult(submission=submission, report=None, analysis_error=error.body)

    @app.post(
        "/submissions/{submission_id}/analyze",
        status_code=201,
        tags=["student"],
        summary="Перезапустить анализ (например, после сбоя аналитики)",
        responses=ERRORS,
    )
    def reanalyze(submission_id: SubmissionId) -> BuildReport:
        return analysis.analyze(submission_id)

    @app.get(
        "/submissions/{submission_id}/file",
        tags=["teacher"],
        response_class=Response,
        responses={200: {"content": {"application/octet-stream": {}}}, **ERRORS},
    )
    def download(submission_id: SubmissionId) -> Response:
        upstream = storage.download(submission_id)
        return Response(
            upstream.content,
            media_type=upstream.headers.get("content-type", "application/octet-stream"),
            headers={"content-disposition": upstream.headers.get("content-disposition", "")},
        )

    @app.get(
        "/assignments/{assignment_id}/reports",
        tags=["teacher"],
        summary="Сводка по заданию: статусы проверок всех сдач",
        responses=ERRORS,
    )
    def assignment_reports(assignment_id: AssignmentId) -> AssignmentSummary:
        return build_summary(
            assignment_id, storage.list(assignment_id), analysis.list(assignment_id)
        )

    @app.get(
        "/assignments/{assignment_id}/dashboard",
        tags=["teacher"],
        summary="Сводка по заданию в виде HTML-страницы",
        response_class=HTMLResponse,
    )
    def dashboard(request: Request, assignment_id: AssignmentId) -> Response:
        summary = assignment_reports(assignment_id)
        return templates.TemplateResponse(request, "dashboard.html", {"summary": summary})

    @app.get(
        "/submissions/{submission_id}/card",
        tags=["teacher"],
        summary="Карточка билда в виде HTML-страницы",
        response_class=HTMLResponse,
    )
    def card(request: Request, submission_id: SubmissionId) -> Response:
        result = get_submission(submission_id)
        return templates.TemplateResponse(request, "card.html", {"result": result})

    return app
