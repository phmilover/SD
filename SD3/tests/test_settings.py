"""Настройки читаются из переменных окружения (их задаёт docker-compose.yml)."""

from pathlib import Path

from analysis_service.settings import Settings as AnalysisSettings
from fastapi.testclient import TestClient
from gateway.app import create_app as create_gateway
from gateway.settings import Settings as GatewaySettings
from storage_service.settings import Settings as StorageSettings


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MAX_FILE_MB", "3")
    monkeypatch.setenv("STORAGE_URL", "http://storage:8001")
    monkeypatch.setenv("ANALYSIS_URL", "http://analysis:8002")
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "2.5")

    assert StorageSettings.from_env() == StorageSettings(Path(tmp_path), 3 * 1024 * 1024)
    assert AnalysisSettings.from_env() == AnalysisSettings(
        Path(tmp_path), "http://storage:8001", 2.5
    )
    assert GatewaySettings.from_env() == GatewaySettings(
        "http://storage:8001", "http://analysis:8002", 2.5, 3 * 1024 * 1024
    )


def test_gateway_with_real_http_clients_reports_services_down():
    # Порт 9 (discard) заведомо никто не слушает: проверяем настоящий сетевой сбой.
    settings = GatewaySettings("http://127.0.0.1:9", "http://127.0.0.1:9", 0.5)
    health = TestClient(create_gateway(settings)).get("/health").json()
    assert health == {"gateway": "ok", "storage": "unavailable", "analysis": "unavailable"}
