"""Приёмка на баланс: проверка номера → техосмотр → постановка на учёт."""

from vyshkat.domain import Asset, DuplicateInventoryNumberError
from vyshkat.services.registry import AssetRegistry
from vyshkat.services.service_center import InspectionResult, ServiceCenter


class IntakeService:
    def __init__(self, registry: AssetRegistry, service_center: ServiceCenter) -> None:
        self._registry = registry
        self._service_center = service_center

    def receive(self, asset: Asset) -> InspectionResult:
        """Принимает объект, если техосмотр его одобрил.

        Raises:
            DuplicateInventoryNumberError: номер уже на балансе — осматривать нечего.
        """
        self.ensure_number_is_free(asset.inventory_number)
        result = self._service_center.inspect(asset)
        if result.approved:
            self._registry.add(asset)
        return result

    def ensure_number_is_free(self, inventory_number: str) -> None:
        """Позволяет проверить номер до создания объекта (консоль делает это сразу после ввода)."""
        if self._registry.contains(inventory_number):
            raise DuplicateInventoryNumberError(inventory_number)
