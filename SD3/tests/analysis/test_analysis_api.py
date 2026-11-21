"""File Analysis Service: берёт файл у хранилища, проверяет, хранит отчёт."""

import httpx

from tests.conftest import make_analysis
from tests.helpers import GOOD_PYTHON, UNKNOWN_ID, make_zip, unreachable


def store(storage, content: bytes, student="Иванов") -> str:
    response = storage.post(
        "/submissions",
        data={"student": student, "assignment_id": "dz-3"},
        files={"file": ("hw.zip", content)},
    )
    return response.json()["submission_id"]


def test_analyze_saves_report(storage, analysis):
    submission_id = store(storage, make_zip(GOOD_PYTHON))
    created = analysis.post("/reports", json={"submission_id": submission_id})
    assert created.status_code == 201
    assert created.json()["status"] == "SUCCESS"
    assert created.json()["student"] == "Иванов"  # метаданные взяты у хранилища

    stored = analysis.get(f"/reports/{submission_id}").json()
    assert stored == created.json()


def test_reanalysis_replaces_the_report(storage, analysis):
    submission_id = store(storage, b"")
    analysis.post("/reports", json={"submission_id": submission_id})
    analysis.post("/reports", json={"submission_id": submission_id})
    assert len(analysis.get("/reports", params={"assignment_id": "dz-3"}).json()) == 1


def test_reports_by_assignment(storage, analysis):
    for student in ("А", "Б"):
        analysis.post("/reports", json={"submission_id": store(storage, b"x", student)})
    reports = analysis.get("/reports", params={"assignment_id": "dz-3"}).json()
    assert [report["student"] for report in reports] == ["А", "Б"]


def test_unknown_submission_is_404(analysis):
    assert analysis.post("/reports", json={"submission_id": UNKNOWN_ID}).status_code == 404
    assert analysis.get(f"/reports/{UNKNOWN_ID}").status_code == 404


def test_malformed_submission_id_is_422(analysis):
    assert analysis.post("/reports", json={"submission_id": "../x"}).status_code == 422


def test_storage_down_gives_clear_503(tmp_path):
    analysis = make_analysis(tmp_path, unreachable())
    response = analysis.post("/reports", json={"submission_id": UNKNOWN_ID})
    assert response.status_code == 503
    assert "File Storing Service недоступен" in response.json()["detail"]


def test_storage_timeout_gives_504(tmp_path):
    analysis = make_analysis(tmp_path, unreachable(httpx.ReadTimeout))
    assert analysis.post("/reports", json={"submission_id": UNKNOWN_ID}).status_code == 504


def test_storage_internal_error_gives_502(tmp_path):
    broken = httpx.Client(
        base_url="http://storage", transport=httpx.MockTransport(lambda _: httpx.Response(500))
    )
    analysis = make_analysis(tmp_path, broken)
    assert analysis.post("/reports", json={"submission_id": UNKNOWN_ID}).status_code == 502
