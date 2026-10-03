"""Автоматический демо-сценарий и пилотный парк для интерактивного режима."""

from collections.abc import Callable

from vyshkat.cli.intake_flow import receive_and_show
from vyshkat.cli.view import FleetView
from vyshkat.domain import (
    Asset,
    Bicycle,
    ChargingCabinet,
    DockStation,
    ElectricBike,
    ElectricScooter,
    Helmet,
    TechnicalCondition,
)
from vyshkat.services import FleetReports, IntakeService


def _worn(percent: int) -> TechnicalCondition:
    return TechnicalCondition(wear_percent=percent)


def _defects(*defects: str) -> TechnicalCondition:
    return TechnicalCondition(defects=defects)


class DemoScenario:
    """Проходит все сценарии из ТЗ без участия пользователя."""

    def __init__(self, intake: IntakeService, reports: FleetReports, view: FleetView) -> None:
        self._intake = intake
        self._reports = reports
        self._view = view

    def run(self) -> None:
        self._view.banner()
        self._view.note("Демо-сценарий: парк пуст, все объекты проходят через IntakeService.")
        self._accept_transport()
        self._reject_by_inspection()
        self._refuse_invalid_records()
        self._accept_items()
        self._show_reports()

    def _accept_transport(self) -> None:
        self._view.section("1. Приём транспорта: исправная техника проходит техосмотр")
        self._receive(
            lambda: ElectricScooter(
                "Ninebot Max G30",
                "VK-TS-001",
                simplicity=8,
                daily_energy_kwh=0.45,
                condition=_worn(5),
            )
        )
        self._receive(lambda: Bicycle("Forward Tracer 29", "VK-B-001", simplicity=9))
        self._receive(
            lambda: ElectricBike("Eltreco XT 850", "VK-EB-001", simplicity=5, daily_energy_kwh=0.6)
        )
        self._receive(
            lambda: ElectricScooter(
                "Kugoo Kirin M4",
                "VK-TS-002",
                simplicity=7,
                daily_energy_kwh=0.5,
                condition=_worn(25),
            )
        )

    def _reject_by_inspection(self) -> None:
        self._view.section("2. Отказ техосмотра: износ выше 30% и дефекты")
        self._receive(
            lambda: ElectricBike(
                "Eltreco XT 850",
                "VK-EB-002",
                simplicity=5,
                daily_energy_kwh=0.6,
                condition=_worn(45),
            )
        )
        self._receive(
            lambda: ElectricScooter(
                "Ninebot Max G30",
                "VK-TS-003",
                simplicity=8,
                daily_energy_kwh=0.45,
                condition=_defects("люфт руля", "не работает задний тормоз"),
            )
        )

    def _refuse_invalid_records(self) -> None:
        self._view.section("3. Ошибки учёта: дубликат номера и некорректные данные")
        self._view.note("Номер VK-TS-001 уже на балансе — повторная приёмка запрещена.")
        self._receive(
            lambda: ElectricScooter("Ninebot", "vk-ts-001", simplicity=8, daily_energy_kwh=0.45)
        )
        self._view.note("«Простота» 11 вне шкалы 1–10 — объект даже не создаётся.")
        self._receive(lambda: Bicycle("Stels Navigator", "VK-B-002", simplicity=11))

    def _accept_items(self) -> None:
        self._view.section("4. Вещи на балансе: шлемы, док-станция, зарядный шкаф")
        self._receive(lambda: Helmet("Шлем Urban M", "VK-H-001"))
        self._receive(
            lambda: DockStation("Док-станция на 10 мест", "VK-D-001", daily_energy_kwh=2.5)
        )
        self._receive(
            lambda: ChargingCabinet("Зарядный шкаф на 12 ячеек", "VK-C-001", daily_energy_kwh=4.0)
        )
        self._receive(
            lambda: Helmet("Шлем Urban L", "VK-H-002", condition=_defects("трещина корпуса"))
        )

    def _show_reports(self) -> None:
        self._view.section("5. Отчёт: число единиц и суммарная энергия")
        self._view.summary(self._reports.summary())

        self._view.section("6. Прокатная техника для новичков")
        self._view.note("Kugoo: простота 7 ≥ 6, но износ 25% > 20% — новичку не выдаём.")
        self._view.novices(
            self._reports.novice_assessments(), self._reports.novice_rule_description()
        )

        self._view.section("7. Наименования и инвентарные номера всей техники и вещей")
        self._view.inventory(self._reports.inventory())

    def _receive(self, build: Callable[[], Asset]) -> None:
        receive_and_show(self._intake, self._view, build)


def pilot_park() -> list[Asset]:
    """Пилотный парк из преамбулы ТЗ: «самокатов пока три» + немного вещей."""
    return [
        ElectricScooter("Ninebot Max G30", "VK-TS-001", simplicity=8, daily_energy_kwh=0.45),
        ElectricScooter("Ninebot Max G30", "VK-TS-002", simplicity=8, daily_energy_kwh=0.45),
        ElectricScooter(
            "Kugoo Kirin M4",
            "VK-TS-003",
            simplicity=5,
            daily_energy_kwh=0.5,
            condition=_worn(15),
        ),
        Helmet("Шлем Urban M", "VK-H-001"),
        DockStation("Док-станция у корпуса на Покровке", "VK-D-001", daily_energy_kwh=2.5),
    ]


def load_pilot_park(intake: IntakeService) -> None:
    """Пилотный парк тоже ставится на баланс только через техосмотр."""
    for asset in pilot_park():
        intake.receive(asset)
