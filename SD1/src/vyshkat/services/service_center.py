"""Техосмотр: решает, можно ли принять новое устройство в парк."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from vyshkat.domain import Asset


@dataclass(frozen=True)
class InspectionResult:
    """Решение техосмотра и причины отказа (пустые при одобрении)."""

    approved: bool
    reasons: tuple[str, ...] = ()

    @classmethod
    def approve(cls) -> "InspectionResult":
        return cls(approved=True)

    @classmethod
    def reject(cls, *reasons: str) -> "InspectionResult":
        if not reasons:
            raise ValueError("Отказ техосмотра должен содержать хотя бы одну причину")
        return cls(approved=False, reasons=reasons)


class ServiceCenter(ABC):
    """Абстракция техосмотра (DIP): приёмка зависит от неё, а не от конкретной политики.

    В контейнере стоит StandardServiceCenter, в тестах — fake/mock через override.
    """

    @abstractmethod
    def inspect(self, asset: Asset) -> InspectionResult: ...


class StandardServiceCenter(ServiceCenter):
    """Базовая политика: без дефектов и с износом не выше порога."""

    def __init__(self, max_wear_percent: int = 30) -> None:
        if not 0 <= max_wear_percent <= 100:
            raise ValueError("Допустимый износ должен быть в диапазоне 0–100%")
        self._max_wear_percent = max_wear_percent

    def inspect(self, asset: Asset) -> InspectionResult:
        condition = asset.condition
        reasons = [f"Дефект: {defect}" for defect in condition.defects]
        if condition.wear_percent > self._max_wear_percent:
            reasons.append(
                f"Износ {condition.wear_percent}% превышает допустимые {self._max_wear_percent}%"
            )
        return InspectionResult.reject(*reasons) if reasons else InspectionResult.approve()
