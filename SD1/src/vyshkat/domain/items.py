"""Вещи на балансе: не выдаются в прокат как транспорт, но инвентаризируются."""

from vyshkat.domain.assets import Asset, TechnicalCondition
from vyshkat.domain.contracts import EnergyConsumer, require_positive_energy


class Item(Asset):
    """Вещь на балансе (шлемы, док-станции, зарядные шкафы…)."""

    category = "Вещи"


class Helmet(Item):
    kind = "Шлем"


class PoweredItem(Item, EnergyConsumer):
    """Стационарное оборудование, подключённое к сети."""

    def __init__(
        self,
        name: str,
        inventory_number: str,
        *,
        daily_energy_kwh: float,
        condition: TechnicalCondition | None = None,
    ) -> None:
        super().__init__(name, inventory_number, condition=condition)
        self._daily_energy_kwh = require_positive_energy(daily_energy_kwh)

    @property
    def daily_energy_kwh(self) -> float:
        return self._daily_energy_kwh


class DockStation(PoweredItem):
    kind = "Док-станция"


class ChargingCabinet(PoweredItem):
    kind = "Зарядный шкаф"
