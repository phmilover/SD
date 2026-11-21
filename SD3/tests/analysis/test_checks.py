"""Алгоритм «проверки на сборку»: какие сдачи зелёные, какие красные и почему."""

from datetime import UTC, datetime

import pytest
from analysis_service.analyzer import Analyzer, SubmissionInfo
from analysis_service.checks import Check

from tests.helpers import GOOD_PYTHON, make_zip


def analyze(content: bytes, filename: str = "hw.zip", analyzer: Analyzer | None = None):
    info = SubmissionInfo(
        submission_id="s1",
        student="Иванов",
        assignment_id="dz-3",
        submitted_at=datetime.now(UTC),
        filename=filename,
    )
    return (analyzer or Analyzer()).analyze(info, content)


def statuses(report) -> dict[str, str]:
    return {check.name: check.status for check in report.checks}


def test_good_python_project_is_green():
    report = analyze(make_zip(GOOD_PYTHON))
    assert report.success and report.status == "SUCCESS"
    assert report.language == "Python"
    assert set(statuses(report).values()) == {"passed"}


def test_empty_file_fails_and_skips_the_rest():
    report = analyze(b"")
    assert not report.success
    assert statuses(report)["not_empty"] == "failed"
    assert all(check.status == "skipped" for check in report.checks[1:])


def test_archive_with_only_readme_fails():
    report = analyze(make_zip({"README.md": "# Сделаю потом"}))
    assert not report.success
    assert statuses(report)["source_code"] == "failed"


def test_broken_zip_fails():
    report = analyze(b"PK\x03\x04 definitely not a zip", filename="hw.zip")
    assert statuses(report)["readable"] == "failed"


def test_python_syntax_error_is_reported_with_line():
    files = {**GOOD_PYTHON, "hw/src/app/broken.py": "def f(:\n    pass\n"}
    report = analyze(make_zip(files))
    syntax = next(check for check in report.checks if check.name == "python_syntax")
    assert syntax.status == "failed"
    assert "broken.py, строка 1" in syntax.message
    assert not report.success


@pytest.mark.parametrize("source", [b"-" * 200_000 + b"1", b"x = 1\x00"])
def test_unparsable_python_does_not_crash_the_service(source):
    files = {**GOOD_PYTHON, "hw/gen.py": source}
    syntax = next(c for c in analyze(make_zip(files)).checks if c.name == "python_syntax")
    assert syntax.status == "failed" and syntax.message.startswith("hw/gen.py")


def test_missing_entry_point_fails():
    report = analyze(make_zip({"lib.py": "def helper():\n    return 1\n"}))
    assert statuses(report)["entry_point"] == "failed"
    report = analyze(b"class Util {}", filename="Util.java")
    assert statuses(report)["entry_point"] == "failed"


def test_plain_python_script_counts_as_entry_point():
    report = analyze(make_zip({"hw/main.py": "print(1)\n"}))
    assert statuses(report)["entry_point"] == "passed"


def test_upper_case_extension_is_still_compiled():
    report = analyze(b"def f(:\n", filename="MAIN.PY")
    assert statuses(report)["python_syntax"] == "failed"


def test_name_main_guard_counts_as_entry_point():
    report = analyze(make_zip({"main.py": "if __name__ == '__main__':\n    print(1)\n"}))
    assert statuses(report)["entry_point"] == "passed"


def test_missing_build_file_and_readme_are_only_warnings():
    report = analyze(make_zip({"main.py": "if __name__ == '__main__':\n    print(1)\n"}))
    assert statuses(report)["build_file"] == "warning"
    assert statuses(report)["readme"] == "warning"
    assert report.success


@pytest.mark.parametrize(
    ("path", "code", "language"),
    [
        ("Main.java", "class Main { public static void main(String[] a) {} }", "Java"),
        ("Program.cs", "class P { static void Main(string[] a) {} }", "C#"),
        ("main.cpp", "int main() { return 0; }", "C++"),
        ("main.go", "package main\nfunc main() {}\n", "Go"),
    ],
)
def test_single_source_file_of_other_languages(path, code, language):
    report = analyze(code.encode(), filename=path)
    assert report.language == language
    assert statuses(report)["entry_point"] == "passed"
    assert statuses(report)["python_syntax"] == "skipped"
    assert report.success


def test_language_without_entry_point_rule_is_skipped():
    report = analyze(make_zip({"index.js": "console.log(1)", "package.json": "{}"}))
    assert statuses(report)["entry_point"] == "skipped"
    assert report.success


def test_dependencies_folder_is_not_counted_as_source():
    report = analyze(make_zip({"README.md": "", ".venv/lib/site.py": "x = 1"}))
    assert statuses(report)["source_code"] == "failed"


def test_new_check_is_added_without_changing_analyzer():
    def no_secrets(project):
        leaked = [path for path in project.files if path.endswith(".env")]
        return ("failed", f"Секреты в сдаче: {leaked}") if leaked else ("passed", "OK")

    analyzer = Analyzer([Check("no_secrets", "Нет секретов", no_secrets)])
    report = analyze(make_zip({".env": "TOKEN=1"}), analyzer=analyzer)
    assert [check.name for check in report.checks] == ["no_secrets"]
    assert not report.success
