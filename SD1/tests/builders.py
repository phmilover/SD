"""Короткие конструкторы тестовых объектов: в тесте видно только то, что важно для проверки."""

from vyshkat.domain import (
    Bicycle,
    ChargingCabinet,
    DockStation,
    ElectricBike,
    ElectricScooter,
    Helmet,
    TechnicalCondition,
)


def scooter(
    number: str = "VK-TS-001",
    *,
    simplicity: int = 7,
    energy: float = 0.4,
    wear: int = 0,
    defects: tuple[str, ...] = (),
) -> ElectricScooter:
    return ElectricScooter(
        "Ninebot Max G30",
        number,
        simplicity=simplicity,
        daily_energy_kwh=energy,
        condition=TechnicalCondition(wear, defects),
    )


def ebike(number: str = "VK-EB-001", *, simplicity: int = 5, energy: float = 0.6) -> ElectricBike:
    return ElectricBike("Eltreco XT 850", number, simplicity=simplicity, daily_energy_kwh=energy)


def bicycle(number: str = "VK-B-001", *, simplicity: int = 9, wear: int = 0) -> Bicycle:
    return Bicycle(
        "Forward Tracer", number, simplicity=simplicity, condition=TechnicalCondition(wear)
    )


def helmet(number: str = "VK-H-001", *, defects: tuple[str, ...] = ()) -> Helmet:
    return Helmet("Шлем Urban M", number, condition=TechnicalCondition(defects=defects))


def dock(number: str = "VK-D-001", *, energy: float = 2.5) -> DockStation:
    return DockStation("Док-станция на 10 мест", number, daily_energy_kwh=energy)


def cabinet(number: str = "VK-C-001", *, energy: float = 4.0) -> ChargingCabinet:
    return ChargingCabinet("Зарядный шкаф на 12 ячеек", number, daily_energy_kwh=energy)
