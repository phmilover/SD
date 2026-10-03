"""Демо-сценарий, пилотный парк и точка входа."""

import builtins

from tests.console_helpers import recording_console
from vyshkat.__main__ import main
from vyshkat.cli.demo import DemoScenario, load_pilot_park
from vyshkat.domain import ElectricScooter


def test_demo_walks_through_every_scenario(container):
    console, output = recording_console()
    container.console.override(console)

    DemoScenario(container.intake(), container.reports(), container.view()).run()

    text = output.getvalue()
    for expected in (
        "Принято на баланс",
        "Отказ техосмотра",
        "уже числится на балансе",
        "Простота для новичка должна быть целым числом от 1 до 10",
        "Суммарное потребление",
        "Можно выдавать новичкам",
        "Инвентарная ведомость",
    ):
        assert expected in text


def test_demo_leaves_only_approved_assets_on_balance(container):
    container.console.override(recording_console()[0])

    DemoScenario(container.intake(), container.reports(), container.view()).run()

    summary = container.reports().summary()
    assert summary.units_by_category == {"Транспорт": 4, "Вещи": 3}


def test_pilot_park_has_three_scooters_that_passed_inspection(container):
    load_pilot_park(container.intake())

    scooters = [a for a in container.registry().all() if isinstance(a, ElectricScooter)]
    assert len(scooters) == 3


def test_main_with_demo_flag_prints_the_demo(capsys):
    main(["--demo"])

    assert "Инвентарная ведомость" in capsys.readouterr().out


def test_main_without_flags_starts_menu_with_pilot_park(capsys, monkeypatch):
    answers = iter(["5", "0"])
    monkeypatch.setattr(builtins, "input", lambda *_: next(answers))

    main([])

    out = capsys.readouterr().out
    assert "VK-TS-001" in out  # пилотный парк уже на балансе
    assert "Доедем до дедлайна" in out
