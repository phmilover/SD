"""Реестр имущества на балансе (хранение в памяти)."""

from vyshkat.domain import Asset, DuplicateInventoryNumberError


class AssetRegistry:
    """Хранит принятое имущество и гарантирует уникальность инвентарных номеров.

    Сознательно без интерфейса: реализация одна, а выделить абстракцию
    (например, для БД) — механическая правка в одном месте. См. README, «DIP ограничен».
    """

    def __init__(self) -> None:
        self._assets: dict[str, Asset] = {}

    def add(self, asset: Asset) -> None:
        if self.contains(asset.inventory_number):
            raise DuplicateInventoryNumberError(asset.inventory_number)
        self._assets[asset.inventory_number] = asset

    def contains(self, inventory_number: str) -> bool:
        return inventory_number.strip().upper() in self._assets

    def all(self) -> list[Asset]:
        return list(self._assets.values())

    def __len__(self) -> int:
        return len(self._assets)
