"""Прокатный транспорт.

Новый вид транспорта = новый подкласс + строка в vyshkat.catalog.ASSET_KINDS.
Отчёты, техосмотр и консоль при этом не меняются (OCP).
"""

from vyshkat.domain.assets import Asset, TechnicalCondition
from vyshkat.domain.contracts import EnergyConsumer, require_positive_energy
from vyshkat.domain.errors import DomainError


class Transport(Asset):
    """Прокатная техника: у каждого вида есть «простота для новичка» (1–10)."""

    category = "Транспорт"

    MIN_SIMPLICITY = 1
    MAX_SIMPLICITY = 10

    def __init__(
        self,
        name: str,
        inventory_number: str,
        *,
        simplicity: int,
        condition: TechnicalCondition | None = None,
    ) -> None:
        super().__init__(name, inventory_number, condition=condition)
        low, high = self.MIN_SIMPLICITY, self.MAX_SIMPLICITY
        is_whole = isinstance(simplicity, int) and not isinstance(simplicity, bool)
        if not (is_whole and low <= simplicity <= high):
            raise DomainError(f"Простота для новичка должна быть целым числом от {low} до {high}")
        self._simplicity = simplicity

    @property
    def simplicity(self) -> int:
        return self._simplicity


class Bicycle(Transport):
    """Обычный велосипед: энергию не потребляет, поэтому EnergyConsumer не реализует."""

    kind = "Велосипед"


class ElectricTransport(Transport, EnergyConsumer):
    """Электротранспорт: заряжается и потребляет энергию."""

    def __init__(
        self,
        name: str,
        inventory_number: str,
        *,
        simplicity: int,
        daily_energy_kwh: float,
        condition: TechnicalCondition | None = None,
    ) -> None:
        super().__init__(name, inventory_number, simplicity=simplicity, condition=condition)
        self._daily_energy_kwh = require_positive_energy(daily_energy_kwh)

    @property
    def daily_energy_kwh(self) -> float:
        return self._daily_energy_kwh


class ElectricScooter(ElectricTransport):
    kind = "Электросамокат"


class ElectricBike(ElectricTransport):
    kind = "Электровелосипед"
