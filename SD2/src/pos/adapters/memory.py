from copy import deepcopy

from pos.domain.errors import DomainError
from pos.domain.model import Gradebook
from pos.domain.ports import GradebookRepository


class InMemoryGradebookRepository(GradebookRepository):
    def __init__(self, initial: Gradebook) -> None:
        self._gradebook = deepcopy(initial)

    def load(self) -> Gradebook:
        return deepcopy(self._gradebook)

    def save(self, gradebook: Gradebook) -> None:
        if gradebook.code != self._gradebook.code:
            raise DomainError("Репозиторий не может заменить ведомость другим курсом")
        self._gradebook = deepcopy(gradebook)
