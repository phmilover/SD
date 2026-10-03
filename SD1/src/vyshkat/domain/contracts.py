"""Узкие интерфейсы-«способности» (ISP): каждый потребитель зависит только от нужного ему.

- отчёт по энергии работает с EnergyConsumer и не знает, самокат это или док-станция;
- инвентарная ведомость работает с Inventoried.
"""

import math
from abc import ABC, abstractmethod

from vyshkat.domain.errors import DomainError


class Inventoried(ABC):
    """Объект на балансе: наименование, вид и обязательный инвентарный номер."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def kind(self) -> str:
        """Вид: «Электросамокат», «Шлем»…

        Конкретные классы задают его атрибутом класса (`kind = "Шлем"`): меню читает вид
        с класса ещё до создания объекта.
        """

    @property
    @abstractmethod
    def inventory_number(self) -> str: ...


class EnergyConsumer(ABC):
    """Устройство, потребляющее электроэнергию."""

    @property
    @abstractmethod
    def daily_energy_kwh(self) -> float:
        """Суточный расход энергии, кВт·ч."""


def require_positive_energy(daily_energy_kwh: float) -> float:
    """Общая проверка для всех реализаций EnergyConsumer."""
    if not (math.isfinite(daily_energy_kwh) and daily_energy_kwh > 0):
        raise DomainError("Суточный расход энергии должен быть больше 0 кВт·ч")
    return float(daily_energy_kwh)
