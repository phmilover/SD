from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

from pos.domain.errors import DomainError
from pos.domain.model import Criterion, Evaluation, Gradebook
from pos.domain.values import clean_text, decimal_number, round_hundredths


def weighted_score(
    criteria: tuple[Criterion, ...], evaluations: tuple[Evaluation, ...]
) -> Fraction:
    by_criterion = {e.criterion.code: e.score.fraction for e in evaluations}
    if not criteria:
        return Fraction(0)
    total_weight = sum((Fraction(c.weight) for c in criteria), Fraction(0))
    return (
        10
        * sum(
            (by_criterion.get(c.code, Fraction(0)) * Fraction(c.weight) for c in criteria),
            Fraction(0),
        )
        / total_weight
    )


class ScoringStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def calculate(
        self, criteria: tuple[Criterion, ...], evaluations: tuple[Evaluation, ...]
    ) -> Fraction: ...


class WeightedAverage(ScoringStrategy):
    name = "По всему рубрикатору (пропуски = 0)"

    def calculate(
        self, criteria: tuple[Criterion, ...], evaluations: tuple[Evaluation, ...]
    ) -> Fraction:
        return weighted_score(criteria, evaluations)


class AssessedOnly(ScoringStrategy):
    name = "Предварительный: только выставленные оценки"

    def calculate(
        self, criteria: tuple[Criterion, ...], evaluations: tuple[Evaluation, ...]
    ) -> Fraction:
        assessed = {e.criterion.code for e in evaluations}
        return weighted_score(tuple(c for c in criteria if c.code in assessed), evaluations)


@dataclass(frozen=True)
class FinalScore:
    value: Decimal
    assessed: int
    total: int
    policy: str

    def __post_init__(self) -> None:
        value = decimal_number(self.value, "Итог")
        if not 0 <= value <= 10:
            raise DomainError("Итог должен быть от 0 до 10")
        if self.total <= 0 or not 0 <= self.assessed <= self.total:
            raise DomainError("Полнота: требуется 0 ≤ оценено ≤ критериев, критериев > 0")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "policy", clean_text(self.policy, "Правило расчёта"))

    @property
    def complete(self) -> bool:
        return self.assessed == self.total


class FinalScoreService:
    """Итог выводится из текущего агрегата; сохранённого итогового балла нет."""

    def __init__(self, strategy: ScoringStrategy) -> None:
        self._strategy = strategy

    @property
    def policy_name(self) -> str:
        return self._strategy.name

    def calculate(self, gradebook: Gradebook, student_code: str) -> FinalScore:
        evaluations = gradebook.evaluations_for(student_code)
        criteria = gradebook.criteria
        if not criteria:
            raise DomainError("Нельзя рассчитать итог: рубрикатор пуст")
        value = self._strategy.calculate(criteria, evaluations)
        if not 0 <= value <= 10:
            raise DomainError("Правило расчёта вернуло итог вне диапазона 0–10")
        return FinalScore(
            value=round_hundredths(value),
            assessed=len(evaluations),
            total=len(criteria),
            policy=self.policy_name,
        )
