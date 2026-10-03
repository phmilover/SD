"""Отчёты по парку. Только чтение: реестр не меняют."""

from collections import Counter
from dataclasses import dataclass

from vyshkat.domain import Asset, EnergyConsumer, Inventoried, Transport
from vyshkat.services.novice_rule import NoviceAssessment, NoviceRule
from vyshkat.services.registry import AssetRegistry


@dataclass(frozen=True)
class KindStats:
    kind: str
    category: str
    units: int
    daily_energy_kwh: float | None  # None — вид не потребляет энергию


@dataclass(frozen=True)
class FleetSummary:
    by_kind: tuple[KindStats, ...]
    # Категории не перечислены жёстко: новая (например, «Запчасть») посчитается сама.
    units_by_category: dict[str, int]
    total_daily_energy_kwh: float

    @property
    def total_units(self) -> int:
        return sum(self.units_by_category.values())


class FleetReports:
    def __init__(self, registry: AssetRegistry, novice_rule: NoviceRule) -> None:
        self._registry = registry
        self._novice_rule = novice_rule

    def summary(self) -> FleetSummary:
        assets = self._registry.all()
        return FleetSummary(
            by_kind=self._stats_by_kind(assets),
            units_by_category=dict(Counter(asset.category for asset in assets)),
            total_daily_energy_kwh=self.total_daily_energy_kwh(),
        )

    def total_daily_energy_kwh(self) -> float:
        return sum(
            (a.daily_energy_kwh for a in self._registry.all() if isinstance(a, EnergyConsumer)),
            start=0.0,
        )

    def novice_assessments(self) -> list[NoviceAssessment]:
        return [
            self._novice_rule.assess(asset)
            for asset in self._registry.all()
            if isinstance(asset, Transport)
        ]

    def novice_rule_description(self) -> str:
        return self._novice_rule.describe()

    def inventory(self) -> list[Inventoried]:
        return sorted(self._registry.all(), key=lambda asset: asset.inventory_number)

    @staticmethod
    def _stats_by_kind(assets: list[Asset]) -> tuple[KindStats, ...]:
        groups: dict[str, list[Asset]] = {}
        for asset in assets:
            groups.setdefault(asset.kind, []).append(asset)

        stats = []
        for kind, group in groups.items():
            consumers = [a for a in group if isinstance(a, EnergyConsumer)]
            energy = sum(c.daily_energy_kwh for c in consumers) if consumers else None
            stats.append(KindStats(kind, group[0].category, len(group), energy))
        return tuple(stats)
