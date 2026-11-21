"""Синхронный HTTP-клиент к File Storing Service: анализ берёт файл у хранилища по id сдачи."""

import httpx
from fastapi import HTTPException

from .analyzer import SubmissionInfo


class StorageClient:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def fetch(self, submission_id: str) -> tuple[SubmissionInfo, bytes]:
        meta = self._get(f"/submissions/{submission_id}")
        content = self._get(f"/submissions/{submission_id}/file").content
        return SubmissionInfo.model_validate(meta.json()), content

    def _get(self, path: str) -> httpx.Response:
        try:
            response = self._http.get(path)
        except httpx.TimeoutException as error:
            raise HTTPException(504, "File Storing Service не ответил вовремя") from error
        except httpx.TransportError as error:
            raise HTTPException(503, "File Storing Service недоступен") from error
        if response.status_code == 404:
            raise HTTPException(404, response.json().get("detail", "Сдача не найдена"))
        if response.is_error:
            raise HTTPException(502, f"File Storing Service вернул {response.status_code}")
        return response
