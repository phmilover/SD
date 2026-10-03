"""Интерактивное меню учёта парка."""

from collections.abc import Callable, Sequence
from typing import Any

from vyshkat.cli.intake_flow import receive_and_show
from vyshkat.cli.prompter import Prompter
from vyshkat.cli.view import FleetView
from vyshkat.domain import (
    Asset,
    DomainError,
    EnergyConsumer,
    Item,
    TechnicalCondition,
    Transport,
    normalize_inventory_number,
)
from vyshkat.services import FleetReports, IntakeService


class ConsoleApp:
    def __init__(
        self,
        intake: IntakeService,
        reports: FleetReports,
        view: FleetView,
        prompter: Prompter,
        catalog: Sequence[type[Asset]],
        demo: Callable[[], None],
    ) -> None:
        self._intake = intake
        self._reports = reports
        self._view = view
        self._prompter = prompter
        self._catalog = catalog
        self._demo = demo
        self._actions: list[tuple[str, Callable[[], None]]] = [
            ("Принять транспорт (техосмотр → баланс)", lambda: self._receive(Transport)),
            ("Поставить вещь на баланс (техосмотр → баланс)", lambda: self._receive(Item)),
            ("Отчёт: число единиц и энергопотребление", self._show_summary),
            ("Техника для новичков", self._show_novices),
            ("Инвентарная ведомость", self._show_inventory),
            ("Демо-сценарий (на отдельном пустом парке)", self._demo),
        ]

    def run(self) -> None:
        self._view.banner()
        try:
            while True:
                self._view.menu([title for title, _ in self._actions])
                choice = self._prompter.integer("Пункт меню", 0, len(self._actions))
                if choice == 0:
                    break
                _, action = self._actions[choice - 1]
                action()
        except (EOFError, KeyboardInterrupt):
            pass  # Ctrl+D / Ctrl+C — обычный выход, а не ошибка
        self._view.goodbye()

    def _receive(self, category: type[Asset]) -> None:
        options = [(k.kind, k) for k in self._catalog if issubclass(k, category)]
        chosen = self._prompter.choice("Вид", options)
        if chosen is not None:
            receive_and_show(self._intake, self._view, lambda: self._ask_asset(chosen))

    def _ask_asset(self, kind: type[Asset]) -> Asset:
        """Спрашивает только те поля, которые нужны виду (по его интерфейсам)."""
        fields: dict[str, Any] = {
            "name": self._prompter.text("Наименование (модель)"),
            "inventory_number": self._ask_inventory_number(),
        }
        if issubclass(kind, Transport):
            low, high = Transport.MIN_SIMPLICITY, Transport.MAX_SIMPLICITY
            fields["simplicity"] = self._prompter.integer(
                f"Простота для новичка ({low}–{high})", low, high
            )
        if issubclass(kind, EnergyConsumer):
            fields["daily_energy_kwh"] = self._prompter.number("Суточный расход энергии, кВт·ч")
        fields["condition"] = TechnicalCondition(
            wear_percent=self._prompter.integer("Износ по результатам осмотра, %", 0, 100),
            defects=self._prompter.items("Дефекты через запятую (Enter — нет)"),
        )
        return kind(**fields)

    def _ask_inventory_number(self) -> str:
        """Номер проверяется сразу: формат и занятость, чтобы не заполнять форму зря."""
        while True:
            try:
                number = normalize_inventory_number(
                    self._prompter.text("Инвентарный номер, например VK-TS-004")
                )
                self._intake.ensure_number_is_free(number)
            except DomainError as error:
                self._view.error(str(error))
                continue
            return number

    def _show_summary(self) -> None:
        self._view.summary(self._reports.summary())

    def _show_novices(self) -> None:
        self._view.novices(
            self._reports.novice_assessments(), self._reports.novice_rule_description()
        )

    def _show_inventory(self) -> None:
        self._view.inventory(self._reports.inventory())
