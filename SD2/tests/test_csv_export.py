import csv

import pytest

from pos.adapters.csv_export import CsvResultsExporter


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=";"))


def test_export_round_trip_preserves_names_and_precision(facade, tmp_path):
    facade.add_student("S", 'Студент; "Альфа"\nПродолжение', "БПИ-01")
    facade.add_criterion("HW", "ДЗ", 10, 1)
    facade.evaluate("S", "HW", "8.25")
    path = tmp_path / "nested" / "results.csv"
    assert facade.export(str(path)) == 1
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert read_csv(path) == [
        {
            "Код": "S",
            "Студент": 'Студент; "Альфа"\nПродолжение',
            "Группа": "БПИ-01",
            "Итог из 10": "8.25",
            "Оценено": "1",
            "Критериев": "1",
            "Правило": facade.policy_name,
        }
    ]


def test_export_replaces_previous_snapshot_with_current_data(populated, tmp_path):
    path = tmp_path / "results.csv"
    populated.evaluate("S-001", "HW", 10)
    populated.export(str(path))
    populated.correct("S-001", "HW", 5)
    populated.export(str(path))
    assert len(read_csv(path)) == 2
    assert read_csv(path)[0]["Итог из 10"] == "1.50"
    assert read_csv(path)[1]["Оценено"] == "0"


def test_course_without_students_exports_only_header(facade, tmp_path):
    facade.add_criterion("HW", "ДЗ", 10, 1)
    path = tmp_path / "results.csv"
    assert facade.export(str(path)) == 0
    assert read_csv(path) == []
    assert "Итог из 10" in path.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("stage", ["create", "write", "sync", "replace"])
@pytest.mark.parametrize("exists", [False, True])
def test_export_failure_preserves_previous_file_and_removes_temporary(
    stage, exists, populated, tmp_path, monkeypatch
):
    path = tmp_path / "results.csv"
    original = b"previous complete report"
    if exists:
        path.write_bytes(original)

    def fail(*args, **kwargs):
        raise OSError("Ошибка записи")

    def interrupted_write(stream, results):
        stream.write("незаконченная строка")
        fail()

    if stage == "create":
        monkeypatch.setattr("pos.adapters.csv_export.NamedTemporaryFile", fail)
    elif stage == "write":
        monkeypatch.setattr(CsvResultsExporter, "_write_rows", staticmethod(interrupted_write))
    else:
        target = "fsync" if stage == "sync" else "replace"
        monkeypatch.setattr(f"pos.adapters.csv_export.os.{target}", fail)

    with pytest.raises(OSError, match="Ошибка записи"):
        populated.export(str(path))
    if exists:
        assert path.read_bytes() == original
    else:
        assert not path.exists()
    assert not list(tmp_path.glob(".pos-*.tmp"))


def test_interrupted_export_preserves_previous_report(populated, tmp_path, monkeypatch):
    path = tmp_path / "results.csv"
    path.write_text("previous report")

    def interrupted(stream, results):
        stream.write("partial data")
        raise KeyboardInterrupt

    monkeypatch.setattr(CsvResultsExporter, "_write_rows", staticmethod(interrupted))
    with pytest.raises(KeyboardInterrupt):
        populated.export(str(path))
    assert path.read_text() == "previous report"
    assert not list(tmp_path.glob(".pos-*.tmp"))
