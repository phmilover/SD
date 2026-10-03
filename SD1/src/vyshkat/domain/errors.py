"""Доменные ошибки: нарушение бизнес-правила, которое можно показать пользователю."""


class DomainError(Exception):
    """Базовая ошибка предметной области (некорректные данные, нарушение правила учёта)."""


class DuplicateInventoryNumberError(DomainError):
    """Инвентарный номер уже числится на балансе."""

    def __init__(self, inventory_number: str) -> None:
        super().__init__(f"Инвентарный номер {inventory_number} уже числится на балансе")
        self.inventory_number = inventory_number
