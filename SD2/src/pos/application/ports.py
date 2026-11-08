from abc import ABC, abstractmethod
from collections.abc import Sequence

from pos.application.reports import StudentResult


class ResultsExporter(ABC):
    """Экспорт заменяет назначение целиком; при ошибке сохраняет прежний результат."""

    @abstractmethod
    def export(self, results: Sequence[StudentResult], destination: str) -> None: ...
