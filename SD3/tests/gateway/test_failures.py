"""Что видит клиент, когда один из сервисов недоступен: понятный ответ, а не обрыв."""

import httpx

from tests.conftest import make_analysis, make_gateway
from tests.helpers import GOOD_PYTHON, make_zip, unreachable


def submit(gateway):
    return gateway.post(
        "/submissions",
        data={"student": "Иванов", "assignment_id": "dz-3"},
        files={"file": ("hw.zip", make_zip(GOOD_PYTHON))},
    )


def test_storage_down_means_nothing_is_saved_and_503(analysis):
    gateway = make_gateway(unreachable(), analysis)
    response = submit(gateway)
    assert response.status_code == 503
    assert response.json() == {
        "error": "service_unavailable",
        "service": "File Storing Service",
        "message": "File Storing Service недоступен, повторите запрос позже",
    }


def test_analysis_down_keeps_submission_and_allows_retry(storage, analysis):
    response = submit(make_gateway(storage, unreachable()))
    assert response.status_code == 202
    body = response.json()
    assert body["report"] is None
    assert body["analysis_error"]["service"] == "File Analysis Service"
    submission_id = body["submission"]["submission_id"]

    # Аналитика поднялась: сдача не потеряна, отчёт получаем повторным запуском.
    healthy = make_gateway(storage, analysis)
    assert healthy.get("/assignments/dz-3/reports").json()["not_analyzed"] == 1
    assert healthy.get(f"/submissions/{submission_id}").json()["report"] is None
    assert healthy.post(f"/submissions/{submission_id}/analyze").status_code == 201
    assert healthy.get("/assignments/dz-3/reports").json()["passed"] == 1


def test_submission_is_shown_even_if_analysis_is_down(storage, analysis):
    submission_id = submit(make_gateway(storage, analysis)).json()["submission"]["submission_id"]
    body = make_gateway(storage, unreachable()).get(f"/submissions/{submission_id}").json()
    assert body["submission"]["submission_id"] == submission_id
    assert body["report"] is None and body["analysis_error"]["error"] == "service_unavailable"


def test_submission_is_shown_even_if_analysis_crashes(storage, analysis):
    submission_id = submit(make_gateway(storage, analysis)).json()["submission"]["submission_id"]
    crashing = httpx.Client(
        base_url="http://analysis", transport=httpx.MockTransport(lambda _: httpx.Response(500))
    )
    body = make_gateway(storage, crashing).get(f"/submissions/{submission_id}").json()
    assert body["report"] is None and body["analysis_error"]["error"] == "service_error"


def test_card_explains_missing_report(storage, analysis):
    gateway = make_gateway(storage, unreachable())
    submission_id = submit(gateway).json()["submission"]["submission_id"]
    card = gateway.get(f"/submissions/{submission_id}/card")
    assert card.status_code == 200
    assert "Отчёта пока нет" in card.text and f"/submissions/{submission_id}/analyze" in card.text


def test_summary_needs_both_services(storage, analysis):
    assert make_gateway(unreachable(), analysis).get("/assignments/dz-3/reports").status_code == 503
    assert make_gateway(storage, unreachable()).get("/assignments/dz-3/reports").status_code == 503


def test_storage_down_behind_analysis_is_reported(tmp_path, storage):
    """Хранилище упало между сохранением и анализом: аналитика отвечает 503, сдача уже есть."""
    blind_analysis = make_analysis(tmp_path, unreachable())
    response = submit(make_gateway(storage, blind_analysis))
    assert response.status_code == 202
    assert "File Storing Service недоступен" in response.json()["analysis_error"]["message"]


def test_timeout_gives_504(analysis):
    response = submit(make_gateway(unreachable(httpx.ReadTimeout), analysis))
    assert response.status_code == 504
    assert response.json()["error"] == "service_timeout"


def test_garbage_from_analysis_still_returns_saved_submission(storage):
    garbage = httpx.Client(
        base_url="http://analysis",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, text="not json")),
    )
    response = submit(make_gateway(storage, garbage))
    assert response.status_code == 202
    assert response.json()["submission"]["submission_id"]
    assert response.json()["analysis_error"]["message"].endswith("вернул некорректный ответ")


def test_internal_error_of_service_gives_502(analysis):
    crashing = httpx.Client(
        base_url="http://storage",
        transport=httpx.MockTransport(lambda _: httpx.Response(500, text="Internal Server Error")),
    )
    response = submit(make_gateway(crashing, analysis))
    assert response.status_code == 502
    assert response.json()["error"] == "service_error"


def test_browser_gets_html_error_page(analysis):
    gateway = make_gateway(unreachable(), analysis)
    response = gateway.get("/assignments/dz-3/dashboard", headers={"accept": "text/html"})
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("text/html")
    assert "недоступен" in response.text


def test_health_shows_which_service_is_down(analysis):
    health = make_gateway(unreachable(), analysis).get("/health").json()
    assert health == {"gateway": "ok", "storage": "unavailable", "analysis": "ok"}
