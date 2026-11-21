"""Все три сервиса в одном процессе: вместо сети — TestClient (это тоже httpx.Client)."""

from pathlib import Path

import pytest
from analysis_service.app import create_app as create_analysis
from analysis_service.settings import Settings as AnalysisSettings
from fastapi.testclient import TestClient
from gateway.app import create_app as create_gateway
from gateway.settings import Settings as GatewaySettings
from storage_service.app import create_app as create_storage
from storage_service.settings import Settings as StorageSettings

MAX_FILE_BYTES = 1024 * 1024


def make_storage(tmp_path: Path) -> TestClient:
    return TestClient(create_storage(StorageSettings(tmp_path / "storage", MAX_FILE_BYTES)))


def make_analysis(tmp_path: Path, storage_http) -> TestClient:
    settings = AnalysisSettings(tmp_path / "analysis", "http://unused", 1)
    return TestClient(create_analysis(settings, storage_http=storage_http))


def make_gateway(storage_http, analysis_http, max_upload_bytes=MAX_FILE_BYTES) -> TestClient:
    settings = GatewaySettings("http://unused", "http://unused", 1, max_upload_bytes)
    return TestClient(create_gateway(settings, storage_http, analysis_http))


@pytest.fixture
def storage(tmp_path: Path) -> TestClient:
    return make_storage(tmp_path)


@pytest.fixture
def analysis(tmp_path: Path, storage: TestClient) -> TestClient:
    return make_analysis(tmp_path, storage)


@pytest.fixture
def gateway(storage: TestClient, analysis: TestClient) -> TestClient:
    return make_gateway(storage, analysis)
