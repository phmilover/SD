"""Базовое имущество на балансе и его техническое состояние."""

import re
from abc import abstractmethod
from dataclasses import dataclass

from vyshkat.domain.contracts import Inventoried
from vyshkat.domain.errors import DomainError

_INVENTORY_NUMBER = re.compile(r"[A-ZА-ЯЁ0-9]+(?:-[A-ZА-ЯЁ0-9]+)*")


def normalize_inventory_number(inventory_number: str) -> str:
    """Приводит номер к виду VK-TS-001 или бросает DomainError.

    Вынесено в функцию, чтобы консоль проверяла номер сразу после ввода по тем же правилам.
    """
    number = inventory_number.strip().upper()
    if not number:
        raise DomainError("Инвентарный номер обязателен")
    if not _INVENTORY_NUMBER.fullmatch(number):
        raise DomainError(
            "Инвентарный номер может содержать только буквы, цифры и дефис, например VK-TS-001"
        )
    return number


@dataclass(frozen=True)
class TechnicalCondition:
    """Состояние на момент приёмки: процент износа и замечания осмотра."""

    wear_percent: int = 0
    defects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.wear_percent <= 100:
            raise DomainError("Износ должен быть в диапазоне 0–100%")
        defects = (self.defects,) if isinstance(self.defects, str) else self.defects
        cleaned = tuple(d.strip() for d in defects if d.strip())
        object.__setattr__(self, "defects", cleaned)


class Asset(Inventoried):
    """Всё, что ставится на баланс «ВышКат»: транспорт и вещи (сотрудники — нет).

    Конкретные подклассы задают `kind` (вид, из контракта Inventoried) атрибутом класса,
    поэтому промежуточные уровни иерархии (Transport, Item) остаются абстрактными.
    """

    def __init__(
        self,
        name: str,
        inventory_number: str,
        *,
        condition: TechnicalCondition | None = None,
    ) -> None:
        self._name = self._validate_name(name)
        self._inventory_number = normalize_inventory_number(inventory_number)
        self._condition = condition or TechnicalCondition()

    @property
    @abstractmethod
    def category(self) -> str:
        """Категория учёта: «Транспорт» или «Вещи»."""

    @property
    def name(self) -> str:
        return self._name

    @property
    def inventory_number(self) -> str:
        return self._inventory_number

    @property
    def condition(self) -> TechnicalCondition:
        return self._condition

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._name!r}, {self._inventory_number!r})"

    @staticmethod
    def _validate_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise DomainError("Наименование не может быть пустым")
        return name
