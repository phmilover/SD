"""Доменная модель «ВышКат»."""

from vyshkat.domain.assets import Asset, TechnicalCondition, normalize_inventory_number
from vyshkat.domain.contracts import EnergyConsumer, Inventoried
from vyshkat.domain.errors import DomainError, DuplicateInventoryNumberError
from vyshkat.domain.items import ChargingCabinet, DockStation, Helmet, Item, PoweredItem
from vyshkat.domain.transport import (
    Bicycle,
    ElectricBike,
    ElectricScooter,
    ElectricTransport,
    Transport,
)

__all__ = [
    "Asset",
    "Bicycle",
    "ChargingCabinet",
    "DockStation",
    "DomainError",
    "DuplicateInventoryNumberError",
    "ElectricBike",
    "ElectricScooter",
    "ElectricTransport",
    "EnergyConsumer",
    "Helmet",
    "Inventoried",
    "Item",
    "PoweredItem",
    "TechnicalCondition",
    "Transport",
    "normalize_inventory_number",
]
