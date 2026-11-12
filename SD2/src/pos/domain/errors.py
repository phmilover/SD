class DomainError(ValueError):
    """Нарушено правило предметной области."""


class DuplicateError(DomainError):
    """Объект с такой идентичностью уже существует."""


class NotFoundError(DomainError):
    """Объект не найден в текущем курсе."""
