from abc import ABC, abstractmethod

from pos.domain.model import Gradebook


class GradebookRepository(ABC):
    """Репозиторий одного курса, без конкурентных записей.

    load возвращает независимый снимок; save заменяет его копией целого агрегата
    того же курса. Неудачный save сохраняет прежнее состояние.
    """

    @abstractmethod
    def load(self) -> Gradebook: ...

    @abstractmethod
    def save(self, gradebook: Gradebook) -> None: ...
