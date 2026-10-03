"""Сценарии интерактивного меню (ввод по сценарию через DI)."""

from tests.builders import bicycle, helmet, scooter

EXIT = BACK = "0"


def test_transport_accepted_after_inspection_is_on_balance(run_app, container):
    output = run_app("1", "1", "Ninebot Max G30", "vk-ts-010", "7", "0,4", "5", "", EXIT)

    assert "Принято на баланс" in output
    assert container.registry().contains("VK-TS-010")


def test_worn_transport_is_rejected_and_reason_is_shown(run_app, container):
    output = run_app("1", "1", "Ninebot Max G30", "VK-TS-011", "7", "0.4", "55", "", EXIT)

    assert "Отказ техосмотра" in output
    assert "Износ 55% превышает допустимые 30%" in output
    assert len(container.registry()) == 0


def test_item_menu_offers_only_items_and_skips_transport_questions(run_app, container):
    # 2 — вещь, 1 — первый вид вещей (шлем): простоту и энергию не спрашиваем.
    output = run_app("2", "1", "Шлем Urban M", "VK-H-010", "0", "трещина", EXIT)

    assert "Электросамокат" not in output
    assert "Дефект: трещина" in output
    assert len(container.registry()) == 0


def test_invalid_inventory_number_is_asked_again_right_away(run_app, container):
    output = run_app("2", "1", "Шлем", "VK 01!", "VK-H-010", "0", "", EXIT)

    assert "только буквы, цифры и дефис" in output
    assert "Принято на баланс" in output
    assert container.registry().contains("VK-H-010")


def test_taken_inventory_number_is_asked_again_right_away(run_app, container):
    container.intake().receive(scooter("VK-TS-001"))

    output = run_app("2", "1", "Шлем", "vk-ts-001", "VK-H-010", "0", "", EXIT)

    assert "VK-TS-001 уже числится на балансе" in output
    assert container.registry().contains("VK-H-010")


def test_kind_choice_offers_a_way_back_to_the_menu(run_app, container):
    output = run_app("1", BACK, "5", EXIT)

    assert "Назад" in output
    assert "Инвентарная ведомость" in output  # вернулись в меню и выбрали другой пункт
    assert len(container.registry()) == 0


def test_summary_report_shows_units_and_energy(run_app, container):
    container.intake().receive(scooter("VK-TS-001", energy=0.4))
    container.intake().receive(helmet("VK-H-001"))

    output = run_app("3", EXIT)

    assert "Транспорт: 1 · Вещи: 1 · Всего единиц: 2" in output
    assert "Суммарное потребление: 0.40 кВт·ч/сут" in output


def test_summary_of_empty_park_says_so(run_app):
    output = run_app("3", EXIT)

    assert "Парк пока пуст" in output
    assert "Всего единиц: 0" in output


def test_novice_report_when_nobody_fits(run_app, container):
    container.intake().receive(bicycle("VK-B-001", simplicity=2))

    output = run_app("4", EXIT)

    assert "Можно выдавать новичкам: 0" in output
    assert "Не для новичков: 1" in output


def test_novice_report_when_everybody_fits(run_app, container):
    container.intake().receive(scooter("VK-TS-001", simplicity=9))

    output = run_app("4", EXIT)

    assert "Можно выдавать новичкам: 1" in output
    assert "Не для новичков" not in output


def test_novice_report_separates_suitable_and_unsuitable_transport(run_app, container):
    container.intake().receive(scooter("VK-TS-001", simplicity=8))
    container.intake().receive(bicycle("VK-B-001", simplicity=3))

    output = run_app("4", EXIT)

    assert "Можно выдавать новичкам" in output
    assert "Не для новичков" in output
    assert "простота 3 < 6" in output


def test_inventory_lists_names_and_numbers(run_app, container):
    container.intake().receive(scooter("VK-TS-001"))
    container.intake().receive(helmet("VK-H-001"))

    output = run_app("5", EXIT)

    assert "VK-TS-001" in output
    assert "Шлем Urban M" in output


def test_demo_menu_item_runs_injected_demo(run_app):
    calls = []

    run_app("6", EXIT, demo=lambda: calls.append("demo"))

    assert calls == ["demo"]


def test_unknown_menu_item_is_asked_again(run_app):
    output = run_app("42", "меню", EXIT)

    assert output.count("целое число от 0 до 6") == 2


def test_end_of_input_finishes_gracefully(run_app):
    output = run_app()

    assert "Доедем до дедлайна" in output
