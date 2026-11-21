"""Сквозной сценарий через Gateway: сдача → хранение → анализ → сводка и визуализация."""

from tests.conftest import make_gateway
from tests.helpers import GOOD_PYTHON, UNKNOWN_ID, make_zip


def submit(gateway, student="Иванов", content=None, assignment="dz-3", name="hw.zip"):
    return gateway.post(
        "/submissions",
        data={"student": student, "assignment_id": assignment},
        files={"file": (name, make_zip(GOOD_PYTHON) if content is None else content)},
    )


def test_submission_is_stored_and_analyzed_in_one_call(gateway, storage, analysis):
    response = submit(gateway)
    assert response.status_code == 201
    body = response.json()
    submission_id = body["submission"]["submission_id"]
    assert body["report"]["status"] == "SUCCESS"
    assert body["analysis_error"] is None
    # Каждый сервис хранит своё: файл — в хранилище, отчёт — в анализе.
    assert storage.get(f"/submissions/{submission_id}").status_code == 200
    assert analysis.get(f"/reports/{submission_id}").status_code == 200


def test_get_submission_with_report(gateway):
    submission_id = submit(gateway, content=b"").json()["submission"]["submission_id"]
    body = gateway.get(f"/submissions/{submission_id}").json()
    assert body["report"]["status"] == "FAILED"


def test_assignment_summary_counts_latest_attempt_of_each_student(gateway):
    submit(gateway, "Иванов", content=b"")  # первая попытка — пустой файл
    submit(gateway, "Иванов")  # исправил
    submit(gateway, "Петров", content=make_zip({"README.md": "скоро"}))
    submit(gateway, "Сидоров", assignment="dz-1")

    summary = gateway.get("/assignments/dz-3/reports").json()
    assert (summary["students"], summary["passed"], summary["failed"]) == (2, 1, 1)
    assert summary["not_analyzed"] == 0
    rows = summary["submissions"]
    assert [(row["submission"]["student"], row["is_latest"]) for row in rows] == [
        ("Иванов", False),
        ("Иванов", True),
        ("Петров", True),
    ]


def test_empty_assignment_summary(gateway):
    summary = gateway.get("/assignments/nobody/reports").json()
    assert summary["students"] == 0 and summary["submissions"] == []


def test_reanalyze_endpoint(gateway):
    submission_id = submit(gateway).json()["submission"]["submission_id"]
    response = gateway.post(f"/submissions/{submission_id}/analyze")
    assert response.status_code == 201 and response.json()["success"]


def test_file_download_through_gateway(gateway):
    submission_id = submit(gateway, content=b"print(1)", name="main.py").json()["submission"][
        "submission_id"
    ]
    response = gateway.get(f"/submissions/{submission_id}/file")
    assert response.content == b"print(1)"
    assert "main.py" in response.headers["content-disposition"]


def test_dashboard_and_build_card_are_html(gateway):
    submit(gateway, "Иванов")
    submission_id = submit(gateway, "Петров", content=b"").json()["submission"]["submission_id"]

    dashboard = gateway.get("/assignments/dz-3/dashboard")
    assert dashboard.headers["content-type"].startswith("text/html")
    assert "Иванов" in dashboard.text and "Петров" in dashboard.text
    assert "SUCCESS" in dashboard.text and "Файл пустой (0 Б)" in dashboard.text

    card = gateway.get(f"/submissions/{submission_id}/card")
    assert "Файл пустой (0 Б)" in card.text and "FAILED" in card.text


def test_client_errors_are_passed_through(gateway):
    response = gateway.get(f"/submissions/{UNKNOWN_ID}")
    assert response.status_code == 404
    assert response.json()["service"] == "File Storing Service"
    assert submit(gateway, student=" ").status_code == 422


def test_bad_input_is_rejected_by_gateway_in_one_format(gateway):
    for response in (
        gateway.get("/submissions/nope"),
        gateway.get("/assignments/dz%203/reports"),
        submit(gateway, assignment="course/task"),
        gateway.post("/submissions", data={"student": "Без файла"}),
    ):
        assert response.status_code == 422
        assert response.json()["service"] == "API Gateway"
    missing = gateway.post("/submissions", data={"student": "Без файла"}).json()["message"]
    assert "file" in missing and "assignment_id" in missing


def test_too_big_upload_is_refused_before_parsing(storage, analysis):
    gateway = make_gateway(storage, analysis, max_upload_bytes=1024)
    response = submit(gateway, content=b"0" * 200_000)
    assert response.status_code == 413 and response.json()["error"] == "too_large"
    assert gateway.get("/assignments/dz-3/reports").json()["students"] == 0


def test_upload_without_content_length_is_refused(gateway):
    def chunks():
        yield b"data"

    response = gateway.post(
        "/submissions", content=chunks(), headers={"content-type": "multipart/form-data"}
    )
    assert response.status_code == 411


def test_swagger_describes_binary_download(gateway):
    spec = gateway.get("/openapi.json").json()["paths"]
    download = spec["/submissions/{submission_id}/file"]["get"]["responses"]["200"]
    assert "application/octet-stream" in download["content"]
    assert {"413", "502", "503"} <= set(spec["/submissions"]["post"]["responses"])


def test_health_and_swagger(gateway):
    assert gateway.get("/health").json() == {
        "gateway": "ok",
        "storage": "ok",
        "analysis": "ok",
    }
    paths = gateway.get("/openapi.json").json()["paths"]
    assert "/submissions" in paths and "/assignments/{assignment_id}/reports" in paths
    assert gateway.get("/", follow_redirects=False).headers["location"] == "/docs"
