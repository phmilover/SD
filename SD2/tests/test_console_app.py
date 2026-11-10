from decimal import Decimal

import pytest

from tests.test_csv_export import read_csv


def test_end_to_end_menu_creates_evaluations_corrects_cancels_and_exports(
    run_app, facade, tmp_path
):
    output = run_app(
        "1",
        "s-001",
        "Студент Альфа",
        "БПИ-01",
        "2",
        "3",
        "hw",
        "ДЗ",
        "10",
        "30",
        "3",
        "project",
        "Проект",
        "20",
        "70",
        "4",
        "5",
        "1",
        "1",
        "9",
        "Первая версия",
        "5",
        "1",
        "2",
        "16",
        "",
        "6",
        "1",
        "9",
        "7",
        "1",
        "1",
        "10",
        "Исправлено",
        "8",
        "1",
        "2",
        "9",
        "10",
        "11",
        "",
        "0",
    )
    assert "8.30" in output
    assert "3.00" in output
    assert "Есть пропуски" in output
    assert "Первая версия" in output
    assert "Оценка исправлена" in output
    assert "Оценка отменена" in output
    assert "Средний итог: 3.00" in output
    assert len(facade.evaluations("S-001")) == 1
    assert facade.result("S-001").final.value == Decimal("3.00")
    assert read_csv(tmp_path / "results.csv")[0]["Итог из 10"] == "3.00"


def test_invalid_numeric_input_is_retried_without_changing_state(populated, run_app):
    output = run_app("5", "1", "1", "12", "-1", "NaN", "буквы", "0,5", "", "0")
    assert output.count("Введите конечное число от 0 до 10") == 2
    assert populated.evaluations("S-001")[0].score.value == Decimal("0.5")


def test_non_positive_rubric_numbers_are_retried(run_app, facade):
    output = run_app("3", "hw", "ДЗ", "0", "Infinity", "10", "-1", "0,3", "0")
    assert output.count("Введите положительное конечное число") == 2
    assert facade.criteria()[0].weight == Decimal("0.3")


def test_empty_name_invalid_code_and_duplicate_code_are_retried(run_app, populated):
    output = run_app("1", "bad code", "s-001", "S-003", "", "Студент Гамма", "", "0")
    assert "только буквы" in output
    assert "Код S-001 уже используется" in output
    assert "Значение не может быть пустым" in output
    assert len(populated.students()) == 3


def test_duplicate_evaluation_returns_to_menu_with_original_score(populated, run_app):
    populated.evaluate("S-001", "HW", 9)
    output = run_app("5", "1", "1", "7", "", "9", "0")
    assert "Оценка уже выставлена" in output
    assert populated.evaluations("S-001")[0].score.value == 9
    assert "2.70" in output


@pytest.mark.parametrize("action", ["5", "6", "7", "8"])
def test_student_selection_can_return_to_menu(action, populated, run_app):
    output = run_app(action, "0", "2", "0")
    assert "Студент Альфа" in output
    assert not populated.evaluations("S-001")


def test_criterion_selection_can_return_to_menu(populated, run_app):
    run_app("5", "1", "0", "0")
    assert populated.evaluations("S-001") == ()


@pytest.mark.parametrize("action", ["7", "8"])
def test_evaluation_selection_can_return_to_menu(action, populated, run_app):
    populated.evaluate("S-001", "HW", 9)
    run_app(action, "1", "0", "0")
    assert populated.evaluations("S-001")[0].score.value == 9


@pytest.mark.parametrize("action", ["5", "6", "7", "8"])
def test_empty_student_selection_does_not_crash(action, run_app):
    output = run_app(action, "0")
    assert "Студент: список пуст" in output
    assert "До встречи" in output


def test_empty_criterion_and_evaluation_selection_do_not_crash(facade, run_app):
    facade.add_student("S", "Студент")
    output = run_app("5", "1", "7", "1", "8", "1", "0")
    assert "Критерий: список пуст" in output
    assert output.count("Выставленная оценка: список пуст") == 2


def test_empty_lists_and_statistics_are_explained(run_app):
    output = run_app("2", "4", "9", "10", "0")
    assert output.count("Список пуст") == 3
    assert "нет данных" in output


def test_empty_rubric_error_is_displayed_and_menu_continues(facade, run_app):
    facade.add_student("S", "Студент")
    output = run_app("9", "2", "0")
    assert "Нельзя рассчитать итог: рубрикатор пуст" in output
    assert "До встречи" in output


def test_export_io_error_is_displayed_and_menu_continues(populated, run_app, tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("occupied")
    output = run_app("11", str(blocked / "results.csv"), "2", "0")
    assert "Ошибка:" in output
    assert "До встречи" in output
    assert blocked.read_text() == "occupied"


def test_demo_callback_runs_without_changing_current_gradebook(populated, run_app):
    calls = []
    output = run_app("12", "0", demo=lambda: calls.append("demo"))
    assert calls == ["demo"]
    assert len(populated.students()) == 2
    assert "До встречи" in output


def test_unknown_menu_choice_is_retried(run_app):
    output = run_app("abc", "13", "-1", "0")
    assert output.count("Введите целое число от 0 до 12") == 3


def test_eof_in_middle_of_form_cancels_incomplete_use_case(run_app, facade):
    output = run_app("1", "S-001", "Студент")
    assert "До встречи" in output
    assert facade.students() == ()


def test_rich_markup_in_user_data_is_printed_literally(run_app, facade):
    output = run_app("1", "S", "[red]Студент[/red]", "", "2", "0")
    assert "[red]Студент[/red]" in output
    assert facade.students()[0].name == "[red]Студент[/red]"


def test_correction_keeps_previous_comment_on_enter(run_app, populated):
    populated.evaluate("S-001", "HW", 7, "Сдано вовремя")
    run_app("7", "1", "1", "8", "", "0")
    evaluation = populated.evaluations("S-001")[0]
    assert evaluation.score.value == 8
    assert evaluation.comment == "Сдано вовремя"
