"""Ввод с консоли: некорректные значения переспрашиваются, программа не падает."""

import pytest

from tests.console_helpers import ScriptedInput, recording_console
from vyshkat.cli.prompter import Prompter


def make_prompter(*lines: str):
    console, output = recording_console()
    return Prompter(console, read_line=ScriptedInput(lines)), output


def test_text_is_trimmed_and_empty_answer_is_asked_again():
    prompter, output = make_prompter("", "  Ninebot  ")

    assert prompter.text("Наименование") == "Ninebot"
    assert "не может быть пустым" in output.getvalue()


def test_integer_asks_again_until_value_is_a_number_in_range():
    prompter, output = make_prompter("семь", "11", "7")

    assert prompter.integer("Простота", 1, 10) == 7
    assert output.getvalue().count("целое число от 1 до 10") == 2


def test_number_accepts_decimal_comma():
    prompter, _ = make_prompter("0,45")

    assert prompter.number("Расход") == pytest.approx(0.45)


@pytest.mark.parametrize("bad", ["0", "-1", "много"])
def test_number_must_be_positive(bad):
    prompter, output = make_prompter(bad, "1.5")

    assert prompter.number("Расход") == 1.5
    assert "положительное число" in output.getvalue()


def test_items_are_split_by_comma_and_empty_answer_means_none():
    prompter, _ = make_prompter("трещина,  люфт руля ,", "")

    assert prompter.items("Дефекты") == ("трещина", "люфт руля")
    assert prompter.items("Дефекты") == ()


def test_choice_lists_options_and_returns_selected_value():
    prompter, output = make_prompter("5", "2")

    assert prompter.choice("Вид", [("Шлем", "helmet"), ("Док-станция", "dock")]) == "dock"
    assert "1. Шлем" in output.getvalue()
    assert "2. Док-станция" in output.getvalue()


def test_choice_zero_means_back():
    prompter, output = make_prompter("0")

    assert prompter.choice("Вид", [("Шлем", "helmet")]) is None
    assert "0. Назад" in output.getvalue()


def test_choice_without_options_is_a_programming_error():
    prompter, _ = make_prompter()

    with pytest.raises(ValueError):
        prompter.choice("Вид", [])


def test_end_of_input_is_propagated_to_the_caller():
    prompter, _ = make_prompter()

    with pytest.raises(EOFError):
        prompter.text("Наименование")
