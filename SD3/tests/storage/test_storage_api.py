"""File Storing Service: хранит сдачи и файлы, отдаёт их обратно байт в байт."""

import hashlib

from tests.conftest import MAX_FILE_BYTES, make_storage


def upload(storage, student="Иванов", assignment="dz-3", content=b"print(1)", name="main.py"):
    return storage.post(
        "/submissions",
        data={"student": student, "assignment_id": assignment},
        files={"file": (name, content)},
    )


def test_upload_saves_metadata_and_file(storage):
    response = upload(storage)
    assert response.status_code == 201
    body = response.json()
    assert body["student"] == "Иванов" and body["assignment_id"] == "dz-3"
    assert body["size_bytes"] == 8
    assert body["sha256"] == hashlib.sha256(b"print(1)").hexdigest()

    file = storage.get(f"/submissions/{body['submission_id']}/file")
    assert file.content == b"print(1)"
    assert "main.py" in file.headers["content-disposition"]


def test_empty_file_is_stored_so_that_analysis_can_fail_it(storage):
    response = upload(storage, content=b"")
    assert response.status_code == 201 and response.json()["size_bytes"] == 0


def test_too_big_file_is_rejected(storage):
    assert upload(storage, content=b"0" * (MAX_FILE_BYTES + 1)).status_code == 413


def test_blank_student_is_rejected(storage):
    assert upload(storage, student="   ").status_code == 422


def test_list_by_assignment_in_upload_order(storage):
    first = upload(storage, student="А").json()["submission_id"]
    second = upload(storage, student="Б").json()["submission_id"]
    upload(storage, assignment="dz-1")
    listed = storage.get("/submissions", params={"assignment_id": "dz-3"}).json()
    assert [item["submission_id"] for item in listed] == [first, second]


def test_unknown_submission_is_404(storage):
    assert storage.get("/submissions/nope").status_code == 404
    assert storage.get("/submissions/nope/file").status_code == 404


def test_data_survives_restart(tmp_path):
    submission_id = upload(make_storage(tmp_path)).json()["submission_id"]
    restarted = make_storage(tmp_path)
    assert restarted.get(f"/submissions/{submission_id}").status_code == 200
