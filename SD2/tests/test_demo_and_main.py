import os
import subprocess
import sys
from io import StringIO

import pytest
from rich.console import Console

from pos.__main__ import main, make_container, run_demo
from pos.domain.errors import DomainError
from tests.test_csv_export import read_csv


def test_demo_runs_full_scenario_and_exports_current_results(container, tmp_path):
    output = StringIO()
    container.console.override(Console(file=output, width=120, color_system=None))
    path = tmp_path / "results.csv"
    container.demo().run(str(path))
    rows = read_csv(path)
    assert [r["Итог из 10"] for r in rows] == ["8.60", "3.00"]
    assert [r["Оценено"] for r in rows] == ["2", "1"]
    assert output.getvalue().count("Ожидаемый отказ") == 3
    assert "После исправления: 8.60/10" in output.getvalue()
    assert "После отмены проекта: 3.00/10" in output.getvalue()


def test_demo_refuses_to_modify_existing_gradebook(populated, container, tmp_path):
    with pytest.raises(DomainError, match="пустую ведомость"):
        container.demo().run(str(tmp_path / "results.csv"))
    assert len(populated.students()) == 2


def test_demo_from_main_uses_selected_strategy(tmp_path, capsys):
    path = tmp_path / "results.csv"
    assert main(["--demo", "--policy", "assessed", "--export", str(path)]) == 0
    assert [r["Итог из 10"] for r in read_csv(path)] == ["8.60", "10.00"]
    assert "Предварительный" in capsys.readouterr().out


def test_demo_default_export_path_is_relative_to_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--demo"]) == 0
    assert (tmp_path / "exports" / "demo-results.csv").exists()


def test_main_reports_export_failure_without_traceback(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("occupied")
    assert main(["--demo", "--export", str(blocker / "results.csv")]) == 1
    assert "Ошибка:" in capsys.readouterr().out


def test_menu_demo_uses_independent_container(tmp_path):
    original = make_container("weighted")
    original.facade().add_student("CUSTOM", "Свой студент")
    path = tmp_path / "demo.csv"
    run_demo("weighted", str(path))
    assert [s.code for s in original.facade().students()] == ["CUSTOM"]
    assert [r["Код"] for r in read_csv(path)] == ["S-001", "S-002"]


def test_main_interactive_menu_can_run_demo_and_exit(tmp_path, monkeypatch):
    answers = iter(["12", "0"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    path = tmp_path / "demo.csv"
    assert main(["--export", str(path)]) == 0
    assert len(read_csv(path)) == 2


def test_keyboard_interrupt_exits_cleanly(monkeypatch, capsys):
    def interrupted(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrupted)
    assert main([]) == 0
    assert "До встречи" in capsys.readouterr().out


def test_module_entry_point_and_eof_exit_without_traceback():
    process = subprocess.run(
        [sys.executable, "-m", "pos"],
        input="",
        text=True,
        capture_output=True,
        env={**os.environ, "NO_COLOR": "1"},
        check=False,
    )
    assert process.returncode == 0
    assert "До встречи" in process.stdout
    assert not process.stderr


def test_demo_detects_silently_accepted_invalid_score(container, monkeypatch, tmp_path):
    monkeypatch.setattr(container.facade(), "correct", lambda *args: None)
    with pytest.raises(RuntimeError, match="не отклонено"):
        container.demo().run(str(tmp_path / "demo.csv"))


def test_keyboard_interrupt_during_demo_exits_without_traceback(monkeypatch, capsys):
    def interrupted(self, export_path):
        raise KeyboardInterrupt

    monkeypatch.setattr("pos.cli.demo.DemoScenario.run", interrupted)
    assert main(["--demo"]) == 130
    assert "До встречи" in capsys.readouterr().out
