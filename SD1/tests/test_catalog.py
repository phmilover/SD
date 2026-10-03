"""Каталог видов: каждый вид проходит весь путь «форма → техосмотр → баланс → отчёты» (LSP/OCP)."""

import pytest

from vyshkat.catalog import ASSET_KINDS
from vyshkat.domain import EnergyConsumer, Transport

EXIT = "0"


def form_answers(kind) -> list[str]:
    """Ответы консольной форме для вида: только те поля, которые вид требует."""
    is_transport = issubclass(kind, Transport)
    same_menu = [k for k in ASSET_KINDS if issubclass(k, Transport) == is_transport]
    answers = ["1" if is_transport else "2", str(same_menu.index(kind) + 1)]
    answers += [f"Тестовый {kind.kind}", "VK-T-001"]
    if is_transport:
        answers.append("7")
    if issubclass(kind, EnergyConsumer):
        answers.append("1,5")
    return [*answers, "0", ""]  # износ 0%, без дефектов


@pytest.mark.parametrize("kind", ASSET_KINDS, ids=lambda kind: kind.__name__)
def test_every_catalog_kind_goes_all_the_way_to_the_reports(run_app, container, kind):
    run_app(*form_answers(kind), EXIT)

    [entry] = container.reports().inventory()
    assert type(entry) is kind
    assert container.reports().summary().units_by_category == {kind.category: 1}
    expected_energy = 1.5 if issubclass(kind, EnergyConsumer) else 0
    assert container.reports().total_daily_energy_kwh() == expected_energy


@pytest.mark.parametrize("kind", ASSET_KINDS, ids=lambda kind: kind.__name__)
def test_every_catalog_kind_declares_titles_as_class_attributes(kind):
    # Меню читает вид с класса, до создания объекта.
    assert isinstance(kind.kind, str)
    assert isinstance(kind.category, str)
