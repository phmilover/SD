"""Синхронные HTTP-клиенты к бизнес-сервисам. Любой сбой превращается в UpstreamError."""

from typing import Any, BinaryIO, TypeVar

import httpx
from pydantic import TypeAdapter, ValidationError

from .schemas import BuildReport, ServiceError, Submission

T = TypeVar("T")

HEALTH_TIMEOUT_SECONDS = 1  # /health должен отвечать быстрее, чем docker healthcheck


class UpstreamError(Exception):
    def __init__(self, status_code: int, error: str, service: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = ServiceError(error=error, service=service, message=message)


class ServiceClient:
    def __init__(self, service: str, http: httpx.Client) -> None:
        self.service = service
        self._http = http

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.TimeoutException as error:
            raise UpstreamError(
                504, "service_timeout", self.service, f"{self.service} не ответил вовремя"
            ) from error
        except httpx.TransportError as error:
            raise UpstreamError(
                503,
                "service_unavailable",
                self.service,
                f"{self.service} недоступен, повторите запрос позже",
            ) from error
        if response.is_success:
            return response
        detail = _detail(response)
        if response.status_code < 500:  # ошибка клиента: 404, 413, 422 — отдаём как есть
            raise UpstreamError(response.status_code, "bad_request", self.service, detail)
        # 503/504 пробрасываем: это аналитика сообщает, что недоступно хранилище.
        status = response.status_code if response.status_code in (503, 504) else 502
        raise UpstreamError(status, "service_error", self.service, detail)

    def parse(self, response: httpx.Response, schema: type[T]) -> T:
        """Ответ не по контракту — тоже сбой сервиса, а не 500 у gateway."""
        try:
            return TypeAdapter(schema).validate_json(response.content)
        except ValidationError as error:
            raise UpstreamError(
                502, "service_error", self.service, f"{self.service} вернул некорректный ответ"
            ) from error

    def is_alive(self) -> bool:
        try:
            return self._http.get("/health", timeout=HEALTH_TIMEOUT_SECONDS).is_success
        except httpx.HTTPError:
            return False


class StorageClient(ServiceClient):
    def __init__(self, http: httpx.Client) -> None:
        super().__init__("File Storing Service", http)

    def upload(
        self, student: str, assignment_id: str, filename: str, content: BinaryIO
    ) -> Submission:
        response = self.request(
            "POST",
            "/submissions",
            data={"student": student, "assignment_id": assignment_id},
            files={"file": (filename, content)},
        )
        return self.parse(response, Submission)

    def get(self, submission_id: str) -> Submission:
        return self.parse(self.request("GET", f"/submissions/{submission_id}"), Submission)

    def list(self, assignment_id: str) -> list[Submission]:
        response = self.request("GET", "/submissions", params={"assignment_id": assignment_id})
        return self.parse(response, list[Submission])

    def download(self, submission_id: str) -> httpx.Response:
        return self.request("GET", f"/submissions/{submission_id}/file")


class AnalysisClient(ServiceClient):
    def __init__(self, http: httpx.Client) -> None:
        super().__init__("File Analysis Service", http)

    def analyze(self, submission_id: str) -> BuildReport:
        response = self.request("POST", "/reports", json={"submission_id": submission_id})
        return self.parse(response, BuildReport)

    def find(self, submission_id: str) -> BuildReport | None:
        try:
            response = self.request("GET", f"/reports/{submission_id}")
        except UpstreamError as error:
            if error.status_code == 404:
                return None
            raise
        return self.parse(response, BuildReport)

    def list(self, assignment_id: str) -> list[BuildReport]:
        response = self.request("GET", "/reports", params={"assignment_id": assignment_id})
        return self.parse(response, list[BuildReport])


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str):
        return detail
    return f"HTTP {response.status_code}: {detail or response.text[:200]}"
